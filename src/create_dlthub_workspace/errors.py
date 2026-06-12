"""CLI-specific exceptions."""

from __future__ import annotations

from pathlib import Path


class WorkspaceError(Exception):
    """Base exception for expected user-facing failures."""


class ScaffoldError(WorkspaceError):
    """Raised when the bundled scaffold cannot be copied into the target directory."""


class WorkspaceDirectoryNotEmptyError(ScaffoldError):
    """Raised when the target directory exists and is not empty.

    Carries the offending path so the CLI can render a dedicated, friendly
    response instead of the generic error line.
    """

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        super().__init__(str(project_dir))


class UvError(WorkspaceError):
    """Raised when uv detection, installation, or execution fails."""
