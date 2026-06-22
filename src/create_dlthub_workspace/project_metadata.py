"""Helpers for customizing generated workspace metadata."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from . import strings
from .errors import ScaffoldError

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def apply_workspace_name(project_dir: Path, workspace_name: str) -> str:
    """Set the generated project's package name and return the normalized value."""
    package_name = normalize_project_name(workspace_name)
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return package_name

    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_WRITE_FAILED.format(path=pyproject, reason=exc)) from exc
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        raise ScaffoldError(strings.ERROR_PARSE_PYPROJECT.format(reason=exc)) from exc

    if "project" not in data:
        return package_name

    try:
        pyproject.write_text(_replace_project_name(content, package_name), encoding="utf-8")
        # The bundled uv.lock pins the root (virtual) package under the scaffold's
        # original name. uv treats the lock as out of date the moment that name no
        # longer matches pyproject, which forces a full re-resolution against the
        # PyPI index — defeating the point of shipping the lock. Rename it in lock-
        # step so `uv sync` installs straight from the lock.
        _replace_lock_project_name(project_dir / "uv.lock", package_name)
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_WRITE_FAILED.format(path=pyproject, reason=exc)) from exc
    return package_name


def normalize_project_name(name: str) -> str:
    """Normalize a directory name into a valid Python distribution name."""
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return normalized or "dlthub-workspace"


def _replace_project_name(content: str, package_name: str) -> str:
    lines = content.splitlines(keepends=True)
    in_project = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[project]":
            in_project = True
            continue
        if in_project and stripped.startswith("["):
            break
        if in_project and re.match(r"^name\s*=", stripped):
            newline = "\n" if line.endswith("\n") else ""
            lines[index] = f'name = "{package_name}"{newline}'
            return "".join(lines)

    insert_at = next(
        (index + 1 for index, line in enumerate(lines) if line.strip() == "[project]"),
        None,
    )
    if insert_at is None:
        return content

    lines.insert(insert_at, f'name = "{package_name}"\n')
    return "".join(lines)


def _replace_lock_project_name(lock_path: Path, package_name: str) -> None:
    """Rename the root (virtual) package in ``uv.lock`` to ``package_name``.

    No-op when the lock is absent or has no virtual root entry. Edits are scoped
    to the ``[[package]]`` block whose ``source = { virtual = "." }`` so unrelated
    dependencies that happen to share the name are never touched, and the rest of
    the file is left byte-for-byte intact (uv is strict about lock formatting).
    """
    if not lock_path.exists():
        return

    lines = lock_path.read_text(encoding="utf-8").splitlines(keepends=True)
    name_index: int | None = None
    in_package = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[[package]]":
            in_package = True
            name_index = None
            continue
        if not in_package:
            continue
        if re.match(r"^name\s*=", stripped):
            name_index = index
        elif stripped == 'source = { virtual = "." }' and name_index is not None:
            newline = "\n" if lines[name_index].endswith("\n") else ""
            lines[name_index] = f'name = "{package_name}"{newline}'
            lock_path.write_text("".join(lines), encoding="utf-8")
            return


def apply_runtime_base_urls(
    project_dir: Path,
    *,
    api_base_url: str | None = None,
    auth_base_url: str | None = None,
) -> None:
    """Pin the given base URLs under ``[runtime]`` in the workspace's ``.dlt/config.toml``.

    ``auth_base_url`` is only needed for stacks that split auth onto its own host (local).
    """
    settings = {
        key: value for key, value in (("api_base_url", api_base_url), ("auth_base_url", auth_base_url)) if value
    }
    if not settings:
        return
    config_path = project_dir / ".dlt" / "config.toml"
    if not config_path.exists():
        return
    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_READ_FAILED.format(path=config_path, reason=exc)) from exc
    for key, value in settings.items():
        content = _set_runtime_key(content, key, value)
    try:
        config_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_WRITE_FAILED.format(path=config_path, reason=exc)) from exc


def apply_dlthub_client_source(project_dir: Path, source: str) -> None:
    """Point the workspace's ``dlthub-client`` at a local checkout via ``[tool.uv.sources]``.

    Added as a direct dependency too — uv only honors a source for a direct dep.
    """
    source_path = Path(source).expanduser().resolve()
    if not (source_path / "pyproject.toml").exists():
        raise ScaffoldError(strings.ERROR_CLIENT_SOURCE_NOT_FOUND.format(path=source_path))
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return
    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_READ_FAILED.format(path=pyproject, reason=exc)) from exc
    content = _add_project_dependency(content, "dlthub-client")
    content = _set_uv_source(content, "dlthub-client", f'{{ path = "{source_path}", editable = true }}')
    try:
        pyproject.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ScaffoldError(strings.ERROR_WRITE_FAILED.format(path=pyproject, reason=exc)) from exc


def _add_project_dependency(content: str, dependency: str) -> str:
    if re.search(rf'^\s*"{re.escape(dependency)}["\[<>=~!,]', content, re.MULTILINE):
        return content
    lines = content.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if re.match(r"^dependencies\s*=\s*\[", line.strip()):
            lines.insert(index + 1, f'    "{dependency}",\n')
            return "".join(lines)
    return content


def _set_uv_source(content: str, name: str, spec: str) -> str:
    entry = f"{name} = {spec}"
    lines = content.splitlines(keepends=True)
    in_sources = False
    sources_index: int | None = None

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[tool.uv.sources]":
            in_sources = True
            sources_index = index
            continue
        if in_sources:
            if stripped.startswith("["):
                break
            if re.match(rf"^{re.escape(name)}\s*=", stripped):
                newline = "\n" if line.endswith("\n") else ""
                lines[index] = f"{entry}{newline}"
                return "".join(lines)

    if sources_index is not None:
        lines.insert(sources_index + 1, f"{entry}\n")
        return "".join(lines)

    separator = "" if content == "" or content.endswith("\n") else "\n"
    return f"{content}{separator}\n[tool.uv.sources]\n{entry}\n"


def _set_runtime_key(content: str, key: str, value: str) -> str:
    entry = f'{key} = "{value}"'
    lines = content.splitlines(keepends=True)
    in_runtime = False
    runtime_index: int | None = None

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[runtime]":
            in_runtime = True
            runtime_index = index
            continue
        if in_runtime:
            if stripped.startswith("["):
                break
            if re.match(rf"^{re.escape(key)}\s*=", stripped):
                newline = "\n" if line.endswith("\n") else ""
                lines[index] = f"{entry}{newline}"
                return "".join(lines)

    if runtime_index is not None:
        lines.insert(runtime_index + 1, f"{entry}\n")
        return "".join(lines)

    separator = "" if content == "" or content.endswith("\n") else "\n"
    return f"{content}{separator}\n[runtime]\n{entry}\n"
