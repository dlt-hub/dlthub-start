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
