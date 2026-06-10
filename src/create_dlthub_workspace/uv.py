"""uv detection, installation, and execution helpers."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import urllib.request
from pathlib import Path

from . import strings
from .errors import UvError

UV_UNIX_INSTALLER = "https://astral.sh/uv/install.sh"
UV_WINDOWS_INSTALLER = "https://astral.sh/uv/install.ps1"


def find_uv() -> str | None:
    """Find uv on PATH or in the default standalone installer locations."""
    found = shutil.which("uv")
    if found:
        return found

    for candidate in _common_uv_paths():
        if candidate.exists():
            return str(candidate)
    return None


def execute_uv_install(*, verbose: bool = False) -> str:
    """Install uv and return its path. Raises if it is not on PATH afterward."""
    install_uv(verbose=verbose)
    uv = find_uv()
    if uv:
        return uv

    raise UvError(strings.ERROR_UV_NOT_ON_PATH)


def install_uv(*, verbose: bool = False) -> None:
    """Install uv with Astral's official standalone installer."""
    system = platform.system().lower()
    if system == "windows":
        _run_windows_installer(verbose=verbose)
    else:
        _run_unix_installer(verbose=verbose)


def run_uv_sync(uv_executable: str, project_dir: Path, *, verbose: bool = False) -> None:
    """Run `uv sync` in the generated workspace."""
    _run([uv_executable, "sync"], cwd=project_dir, isolated_project=True, verbose=verbose)


def run_uv_command(
    uv_executable: str,
    project_dir: Path,
    args: list[str],
    *,
    verbose: bool = False,
) -> None:
    """Run a uv command in the generated workspace."""
    _run([uv_executable, *args], cwd=project_dir, isolated_project=True, verbose=verbose)


def capture_uv_command(uv_executable: str, project_dir: Path, args: list[str]) -> str:
    """Run a uv command in the generated workspace and return its captured stdout."""
    try:
        result = subprocess.run(
            [uv_executable, *args],
            cwd=project_dir,
            env=_isolated_project_env(),
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise UvError(strings.ERROR_UV_COMMAND_NOT_FOUND.format(cmd=uv_executable)) from exc
    except subprocess.CalledProcessError as exc:
        joined = " ".join([uv_executable, *args])
        raise UvError(strings.ERROR_UV_COMMAND_FAILED.format(returncode=exc.returncode, cmd=joined)) from exc
    return result.stdout


def _run_unix_installer(*, verbose: bool = False) -> None:
    try:
        with urllib.request.urlopen(UV_UNIX_INSTALLER, timeout=30) as response:
            script = response.read()
    except OSError as exc:
        raise UvError(strings.ERROR_UV_INSTALLER_FETCH.format(reason=exc)) from exc

    _run(["sh"], input_bytes=script, verbose=verbose)


def _run_windows_installer(*, verbose: bool = False) -> None:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        raise UvError(strings.ERROR_UV_NEEDS_POWERSHELL)

    try:
        with urllib.request.urlopen(UV_WINDOWS_INSTALLER, timeout=30) as response:
            script = response.read()
    except OSError as exc:
        raise UvError(strings.ERROR_UV_INSTALLER_FETCH.format(reason=exc)) from exc

    _run(
        [powershell, "-ExecutionPolicy", "ByPass", "-Command", "-"],
        input_bytes=script,
        verbose=verbose,
    )


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
    isolated_project: bool = False,
    verbose: bool = False,
) -> None:
    try:
        subprocess.run(
            command,
            cwd=cwd,
            env=_isolated_project_env() if isolated_project else None,
            input=input_bytes,
            check=True,
            capture_output=not verbose,
        )
    except FileNotFoundError as exc:
        raise UvError(strings.ERROR_UV_COMMAND_NOT_FOUND.format(cmd=command[0])) from exc
    except subprocess.CalledProcessError as exc:
        joined = " ".join(command)
        message = strings.ERROR_UV_COMMAND_FAILED.format(returncode=exc.returncode, cmd=joined)
        if not verbose:
            captured = _format_captured(exc.stderr, exc.stdout)
            if captured:
                message = f"{message}\n\n{captured}"
        raise UvError(message) from exc


def _format_captured(stderr: bytes | None, stdout: bytes | None) -> str:
    parts: list[str] = []
    for stream in (stderr, stdout):
        if not stream:
            continue
        decoded = stream.decode("utf-8", errors="replace").rstrip()
        if decoded:
            parts.append(decoded)
    return "\n\n".join(parts)


def _common_uv_paths() -> tuple[Path, ...]:
    home = Path.home()
    if os.name == "nt":
        return (
            home / ".local" / "bin" / "uv.exe",
            home / ".cargo" / "bin" / "uv.exe",
        )
    return (
        home / ".local" / "bin" / "uv",
        home / ".cargo" / "bin" / "uv",
    )


def _isolated_project_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in ("VIRTUAL_ENV", "CONDA_PREFIX", "PYTHONPATH"):
        env.pop(name, None)
    return env
