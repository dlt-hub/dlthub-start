"""Tests for the telemetry module."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import MagicMock, patch

from create_dlthub_workspace import telemetry
from create_dlthub_workspace.cli import main
from create_dlthub_workspace.errors import WorkspaceDirectoryNotEmptyError, WorkspaceError

_OPT_OUT_ENV = ("DLTHUB_START_TELEMETRY", "DO_NOT_TRACK", "RUNTIME__DLTHUB_TELEMETRY")


@contextlib.contextmanager
def _silenced() -> Iterator[None]:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


@contextlib.contextmanager
def _clean_opt_out_env() -> Iterator[None]:
    """Drop every opt-out signal so a test starts from the default-enabled state."""
    with patch.dict(os.environ, {}, clear=False):
        for name in _OPT_OUT_ENV:
            os.environ.pop(name, None)
        yield


class IsEnabledTests(unittest.TestCase):
    def test_no_telemetry_flag_disables(self) -> None:
        self.assertFalse(telemetry._is_enabled(True))

    def test_env_zero_disables(self) -> None:
        with patch.dict(os.environ, {"DLTHUB_START_TELEMETRY": "0"}):
            self.assertFalse(telemetry._is_enabled(False))

    def test_env_one_enables_overriding_dlt(self) -> None:
        with patch.dict(os.environ, {"DLTHUB_START_TELEMETRY": "1"}):
            self.assertTrue(telemetry._is_enabled(False))

    def test_do_not_track_disables(self) -> None:
        with _clean_opt_out_env():
            os.environ["DO_NOT_TRACK"] = "1"
            self.assertFalse(telemetry._is_enabled(False))


class DltOptOutTests(unittest.TestCase):
    def _is_enabled_with_config(self, contents: str | None) -> bool:
        with tempfile.TemporaryDirectory() as global_dir:
            if contents is not None:
                (Path(global_dir) / "config.toml").write_text(contents, encoding="utf-8")
            with _clean_opt_out_env(), patch.object(telemetry, "_dlt_global_dir", return_value=Path(global_dir)):
                return telemetry._is_enabled(False)

    def test_dlt_opt_out_disables(self) -> None:
        self.assertFalse(self._is_enabled_with_config("[runtime]\ndlthub_telemetry = false\n"))

    def test_dlt_opt_in_enabled(self) -> None:
        self.assertTrue(self._is_enabled_with_config("[runtime]\ndlthub_telemetry = true\n"))

    def test_no_config_enabled_by_default(self) -> None:
        self.assertTrue(self._is_enabled_with_config(None))

    def test_non_utf8_config_do_not_crash_cli(self) -> None:
        with tempfile.TemporaryDirectory() as global_dir:
            (Path(global_dir) / "config.toml").write_bytes("[runtime]\n".encode("utf-16"))
            with _clean_opt_out_env(), patch.object(telemetry, "_dlt_global_dir", return_value=Path(global_dir)):
                self.assertTrue(telemetry._is_enabled(False))

    def test_runtime_env_override_disables(self) -> None:
        with _clean_opt_out_env():
            os.environ["RUNTIME__DLTHUB_TELEMETRY"] = "false"
            self.assertFalse(telemetry._is_enabled(False))


class ProjectKeyTests(unittest.TestCase):
    def test_env_override_wins(self) -> None:
        with patch.dict(os.environ, {"DLTHUB_START_POSTHOG_KEY": "phc_env"}):
            self.assertEqual(telemetry._project_key(), "phc_env")

    def test_empty_without_baked_key_or_env(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DLTHUB_START_POSTHOG_KEY", None)
            self.assertEqual(telemetry._project_key(), "")

    def test_init_is_noop_without_a_key(self) -> None:
        instance = telemetry._Telemetry()
        with patch.dict(os.environ, {"DLTHUB_START_TELEMETRY": "1"}):
            os.environ.pop("DLTHUB_START_POSTHOG_KEY", None)
            instance.init(no_telemetry=False, interactive=True)
        self.assertIsNone(instance._client)


class InitTests(unittest.TestCase):
    def test_init_never_propagates_errors(self) -> None:
        instance = telemetry._Telemetry()
        with patch.dict(os.environ, {"DLTHUB_START_POSTHOG_KEY": "phc_x"}):
            with patch.object(telemetry, "_is_enabled", side_effect=ValueError("boom")):
                instance.init(no_telemetry=False, interactive=True)  # must not raise
        self.assertIsNone(instance._client)


class DeviceIdTests(unittest.TestCase):
    def test_creates_hex_id_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as global_dir:
            with patch.object(telemetry, "_dlt_global_dir", return_value=Path(global_dir)):
                device_id = telemetry._device_id()
        self.assertEqual(len(device_id), 32)
        int(device_id, 16)  # raises if not hex

    def test_reads_existing_id(self) -> None:
        with tempfile.TemporaryDirectory() as global_dir:
            (Path(global_dir) / ".anonymous_id").write_text("existing-id", encoding="utf-8")
            with patch.object(telemetry, "_dlt_global_dir", return_value=Path(global_dir)):
                self.assertEqual(telemetry._device_id(), "existing-id")

    def test_persists_stable_id_without_newline(self) -> None:
        with tempfile.TemporaryDirectory() as global_dir:
            with patch.object(telemetry, "_dlt_global_dir", return_value=Path(global_dir)):
                first = telemetry._device_id()
                second = telemetry._device_id()
            stored = (Path(global_dir) / ".anonymous_id").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertEqual(stored, first)


@contextlib.contextmanager
def _global_dir_env(home: str, **overrides: str) -> Iterator[None]:
    with patch.object(telemetry.os.path, "expanduser", return_value=home):
        with patch.dict(os.environ, {}, clear=False):
            for name in ("XDG_DATA_HOME", "DLT_CONFIG_FOLDER", "DLT_DATA_DIR"):
                os.environ.pop(name, None)
            os.environ.update(overrides)
            yield


_XDG_HOME = "/xdg-data-home"

_GLOBAL_DIR_CASES = [
    ("home default when no XDG", {}, None, lambda home: home / ".dlt"),
    ("XDG used when ~/.dlt absent", {"XDG_DATA_HOME": _XDG_HOME}, None, lambda home: Path(_XDG_HOME) / "dlt"),
    ("XDG ignored when ~/.dlt present", {"XDG_DATA_HOME": _XDG_HOME}, ".dlt", lambda home: home / ".dlt"),
    ("DLT_CONFIG_FOLDER renames the home folder", {"DLT_CONFIG_FOLDER": ".cfg"}, None, lambda home: home / ".cfg"),
    (
        "DLT_CONFIG_FOLDER drives the XDG existence check",
        {"XDG_DATA_HOME": _XDG_HOME, "DLT_CONFIG_FOLDER": ".cfg"},
        None,
        lambda home: Path(_XDG_HOME) / "dlt",
    ),
    (
        "DLT_CONFIG_FOLDER folder present beats XDG",
        {"XDG_DATA_HOME": _XDG_HOME, "DLT_CONFIG_FOLDER": ".cfg"},
        ".cfg",
        lambda home: home / ".cfg",
    ),
    ("DLT_DATA_DIR is ignored", {"DLT_DATA_DIR": "/data-dir"}, None, lambda home: home / ".dlt"),
]


class GlobalDirTests(unittest.TestCase):
    def setUp(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("resolution differs for root")

    def test_resolution_matrix(self) -> None:
        for label, env, precreate, expected in _GLOBAL_DIR_CASES:
            with self.subTest(label):
                with tempfile.TemporaryDirectory() as home:
                    if precreate:
                        (Path(home) / precreate).mkdir()
                    with _global_dir_env(home, **env):
                        self.assertEqual(telemetry._dlt_global_dir(), expected(Path(home)))

    def test_temp_fallback_when_home_unresolved(self) -> None:
        with _global_dir_env("~"):
            self.assertEqual(telemetry._dlt_global_dir(), Path(tempfile.gettempdir()) / "dlt")

    def test_temp_fallback_when_home_unwritable(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            with _global_dir_env(home), patch.object(telemetry, "_is_writable", return_value=False):
                self.assertEqual(telemetry._dlt_global_dir(), Path(tempfile.gettempdir()) / "dlt")


class CiDetectionTests(unittest.TestCase):
    def test_detects_ci(self) -> None:
        with patch.dict(os.environ, {"CI": "true"}):
            self.assertTrue(telemetry._is_ci())

    def test_no_ci(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(telemetry._is_ci())


class EventShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.t = telemetry._Telemetry()
        self.t._client = self.client
        self.t._distinct_id = "device-123"
        self.t._base = telemetry._base_properties("device-123", interactive=True)
        self.t._started_at = time.monotonic()

    def _kwargs(self) -> dict[str, Any]:
        return self.client.capture.call_args.kwargs

    def test_track_run_emits_taxonomy_event(self) -> None:
        self.t.track_run("success")
        kwargs = self._kwargs()
        self.assertEqual(kwargs["event"], "visitor:run:uvx_command")
        self.assertEqual(kwargs["distinct_id"], "device-123")
        self.assertIn("uuid", kwargs)  # dedup id, like the runtime tracker
        self.assertIn("timestamp", kwargs)  # server-side event time
        props = kwargs["properties"]
        self.assertEqual(props["actor_type"], "visitor")
        self.assertEqual(props["actor_id"], "device-123")
        self.assertEqual(props["object_type"], "uvx_command")
        self.assertEqual(props["object_id"], "dlthub-start")
        self.assertEqual(props["context"], "uvx-start")
        self.assertEqual(props["source"], "uvx")
        self.assertEqual(props["device_id"], "device-123")
        self.assertEqual(props["cli_version"], telemetry.VERSION)
        self.assertIn("session_id", props)

    def test_track_run_success(self) -> None:
        self.t.track_run("success")
        props = self._kwargs()["properties"]
        self.assertEqual(props["status"], "success")
        self.assertIn("duration_ms", props)
        self.assertNotIn("error_code", props)

    def test_track_run_failed_carries_error_code(self) -> None:
        self.t.track_run("failed", error_code="WorkspaceError")
        props = self._kwargs()["properties"]
        self.assertEqual(props["status"], "failed")
        self.assertEqual(props["error_code"], "WorkspaceError")

    def test_track_run_cancelled_drops_error_code(self) -> None:
        self.t.track_run("cancelled", error_code="KeyboardInterrupt")
        props = self._kwargs()["properties"]
        self.assertEqual(props["status"], "cancelled")
        self.assertNotIn("error_code", props)

    def test_track_run_emits_once(self) -> None:
        self.t.track_run("success")
        self.t.track_run("failed", error_code="X")
        self.client.capture.assert_called_once()

    def test_track_run_is_noop_when_disabled(self) -> None:
        self.t._client = None
        self.t.track_run("success")

    def test_track_run_swallows_client_errors(self) -> None:
        self.client.capture.side_effect = RuntimeError("network down")
        self.t.track_run("success")


class MainWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.track_run = patch("create_dlthub_workspace.telemetry.track_run").start()
        patch("create_dlthub_workspace.telemetry.init").start()
        patch("create_dlthub_workspace.cli.stdin_is_interactive", return_value=False).start()
        self.cli_run = patch("create_dlthub_workspace.cli.run").start()
        self.addCleanup(patch.stopall)

    def _main(self) -> int:
        with _silenced():
            return main([])

    def test_success_path(self) -> None:
        rc = self._main()
        self.assertEqual(rc, 0)
        self.track_run.assert_called_once_with("success")

    def test_cancelled_path(self) -> None:
        self.cli_run.side_effect = KeyboardInterrupt()
        rc = self._main()
        self.assertEqual(rc, 130)
        self.track_run.assert_called_once_with("cancelled")

    def test_workspace_error_path(self) -> None:
        self.cli_run.side_effect = WorkspaceError("boom")
        rc = self._main()
        self.assertEqual(rc, 1)
        self.track_run.assert_called_once_with("failed", error_code="WorkspaceError")

    def test_unexpected_error_path(self) -> None:
        self.cli_run.side_effect = RuntimeError("kaboom")
        rc = self._main()
        self.assertEqual(rc, 1)
        self.track_run.assert_called_once_with("failed", error_code="RuntimeError")

    def test_dir_not_empty_path(self) -> None:
        self.cli_run.side_effect = WorkspaceDirectoryNotEmptyError(Path("/x"))
        rc = self._main()
        self.assertEqual(rc, 2)
        self.track_run.assert_called_once_with("failed", error_code="WorkspaceDirectoryNotEmptyError")


class FirstRunNoticeTests(unittest.TestCase):
    def test_shows_notice_only_once(self) -> None:
        with tempfile.TemporaryDirectory() as global_dir:
            with patch.object(telemetry, "_dlt_global_dir", return_value=Path(global_dir)):
                with patch.object(telemetry.console, "print") as printer:
                    telemetry._show_first_run_notice()
                    telemetry._show_first_run_notice()
        printer.assert_called_once()

    def test_method_is_noop_when_telemetry_disabled(self) -> None:
        t = telemetry._Telemetry()
        with patch.object(telemetry, "_show_first_run_notice") as notice:
            t.show_first_run_notice()
        notice.assert_not_called()

    def test_method_shows_notice_when_active(self) -> None:
        t = telemetry._Telemetry()
        t._client = MagicMock()
        with patch.object(telemetry, "_show_first_run_notice") as notice:
            t.show_first_run_notice()
        notice.assert_called_once()

    def test_method_never_propagates_errors(self) -> None:
        t = telemetry._Telemetry()
        t._client = MagicMock()
        with patch.object(telemetry, "_show_first_run_notice", side_effect=ValueError("boom")):
            t.show_first_run_notice()


if __name__ == "__main__":
    unittest.main()
