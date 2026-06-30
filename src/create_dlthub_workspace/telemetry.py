"""Usage telemetry for the dlthub-start CLI."""

from __future__ import annotations

import atexit
import logging
import os
import secrets
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from . import strings
from .config import POSTHOG_HOST, VERSION
from .display import console

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

try:
    from ._telemetry_key import POSTHOG_PROJECT_KEY  # type: ignore[import-untyped]
except (ImportError, SyntaxError):
    POSTHOG_PROJECT_KEY = ""


EVENT_NAME = "visitor:run:uvx_command"
_ACTOR_TYPE = "visitor"
_OBJECT_TYPE = "uvx_command"
_OBJECT_ID = "dlthub-start"
_CONTEXT = "uvx-start"
_SOURCE = "uvx"

RunStatus = Literal["success", "failed", "cancelled"]

_REQUEST_TIMEOUT_SECONDS = 3
_ANONYMOUS_ID_FILE = ".anonymous_id"
_NOTICE_MARKER_FILE = ".dlthub_start_telemetry_notice"
_TRUTHY = {"1", "true", "yes", "on"}


class _Telemetry:
    def __init__(self) -> None:
        self._client: Any = None
        self._distinct_id = ""
        self._base: dict[str, object] = {}
        self._started_at = 0.0
        self._emitted = False

    def init(self, *, no_telemetry: bool, interactive: bool) -> None:
        """Start the telemetry client once per process, unless the user opted out."""
        if self._client is not None:
            return
        try:
            key = _project_key()
            if not key or not _is_enabled(no_telemetry):
                return
            # lazy import to speed up the disabled paths
            import posthog  # noqa: PLC0415

            self._distinct_id = _device_id()
            self._base = _base_properties(self._distinct_id, interactive)
            self._started_at = time.monotonic()
            _silence_posthog_logging()
            self._client = posthog.Posthog(
                key,
                host=_host(),
                max_retries=0,
                timeout=_REQUEST_TIMEOUT_SECONDS,
                disable_geoip=True,
            )
            atexit.register(self.shutdown)
        except Exception:
            self._client = None

    def show_first_run_notice(self) -> None:
        if self._client is None:
            return
        try:
            _show_first_run_notice()
        except Exception:
            pass

    def track_run(self, status: RunStatus, error_code: str | None = None) -> None:
        if self._emitted:
            return
        self._emitted = True
        self._emit(status, error_code)

    def _emit(self, status: RunStatus, error_code: str | None = None) -> None:
        if self._client is None:
            return
        properties: dict[str, object] = {
            **self._base,
            "status": status,
            "duration_ms": self.elapsed_ms(),
        }
        if error_code is not None and status == "failed":
            properties["error_code"] = error_code
        try:
            self._client.capture(
                event=EVENT_NAME,
                distinct_id=self._distinct_id,
                properties=properties,
                timestamp=datetime.now(tz=timezone.utc),
                uuid=str(uuid.uuid4()),
            )
        except Exception:
            pass

    def elapsed_ms(self) -> int:
        """Milliseconds since the run started."""
        return int((time.monotonic() - self._started_at) * 1000)

    def shutdown(self) -> None:
        """Flush queued events on exit."""
        client, self._client = self._client, None
        if client is None:
            return
        try:
            client.flush()
        except Exception:
            pass


_telemetry = _Telemetry()


def init(*, no_telemetry: bool, interactive: bool) -> None:
    _telemetry.init(no_telemetry=no_telemetry, interactive=interactive)


def show_first_run_notice() -> None:
    _telemetry.show_first_run_notice()


def track_run(status: RunStatus, error_code: str | None = None) -> None:
    _telemetry.track_run(status, error_code)


def _is_enabled(no_telemetry: bool) -> bool:
    if no_telemetry:
        return False
    explicit = os.environ.get("DLTHUB_START_TELEMETRY")
    if explicit is not None:
        return _is_truthy(explicit)
    if _is_truthy(os.environ.get("DO_NOT_TRACK")):
        return False
    return _dlt_telemetry_enabled()


def _dlt_telemetry_enabled() -> bool:
    """Honor an existing dlt opt-out."""
    override = os.environ.get("RUNTIME__DLTHUB_TELEMETRY")
    if override is not None:
        return _is_truthy(override)
    try:
        config = tomllib.loads((_dlt_global_dir() / "config.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return True
    runtime = config.get("runtime")
    return not (isinstance(runtime, dict) and runtime.get("dlthub_telemetry") is False)


def _is_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in _TRUTHY


def _device_id() -> str:
    """Read, or create, the dlt device id."""
    path = _dlt_global_dir() / _ANONYMOUS_ID_FILE
    try:
        existing = path.read_text(encoding="utf-8").strip()
    except OSError:
        existing = ""
    if existing:
        return existing
    device_id = secrets.token_hex(16)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(device_id, encoding="utf-8")
    except OSError:
        pass
    return device_id


def _dlt_global_dir() -> Path:
    """Resolve dlt's global directory."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return Path("/var") / "dlt"
    home = os.path.expanduser("~")
    if home == "~" or not _is_writable(Path(home)):
        return Path(tempfile.gettempdir()) / "dlt"
    dot_dlt = os.environ.get("DLT_CONFIG_FOLDER", ".dlt")
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg and not (Path(home) / dot_dlt).is_dir():
        return Path(xdg) / "dlt"
    return Path(home) / dot_dlt


def _is_writable(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK)


def _base_properties(device_id: str, interactive: bool) -> dict[str, object]:
    return {
        "actor_type": _ACTOR_TYPE,
        "actor_id": device_id,
        "object_type": _OBJECT_TYPE,
        "object_id": _OBJECT_ID,
        "context": _CONTEXT,
        "source": _SOURCE,
        "device_id": device_id,
        "session_id": secrets.token_hex(16),
        "cli_version": VERSION,
        "ci": _is_ci(),
        "interactive": interactive,
    }


def _is_ci() -> bool:
    return bool(os.environ.get("CI"))


def _project_key() -> str:
    return os.environ.get("DLTHUB_START_POSTHOG_KEY") or POSTHOG_PROJECT_KEY


def _host() -> str:
    return os.environ.get("DLTHUB_START_POSTHOG_HOST") or POSTHOG_HOST


def _silence_posthog_logging() -> None:
    posthog_logger = logging.getLogger("posthog")
    posthog_logger.addHandler(logging.NullHandler())
    posthog_logger.propagate = False


def _show_first_run_notice() -> None:
    marker = _dlt_global_dir() / _NOTICE_MARKER_FILE
    if marker.exists():
        return
    console.print(strings.MSG_TELEMETRY_NOTICE)
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        pass
