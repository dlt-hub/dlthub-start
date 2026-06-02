"""Copy a bundled scaffold into a new workspace directory."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import strings
from .errors import ScaffoldError

SCAFFOLDS_DIR = Path(__file__).parent / "scaffolds"

# Subdirectory under each scaffold that holds the per-agent vendored AI files
# (`_agents/<agent>/...`). `generate_ai.py` writes them; copy_scaffold lays
# down the selected agent's tree at scaffold time.
PER_AGENT_DIR = "_agents"

# The vendored `.dlt/.toolkits` manifest stores an `installed_at` ISO timestamp
# per toolkit. We commit it with this sentinel so `check-ai` diffs stay clean
# across machines; copy_scaffold replaces it with the real install time when
# the user actually creates a workspace.
TOOLKITS_MANIFEST = Path(".dlt") / ".toolkits"
INSTALL_TIME_SENTINEL = "1970-01-01T00:00:00+00:00"


def validate_target_dir(project_dir: Path) -> None:
    """Refuse to write into a non-empty existing directory. No filesystem writes."""
    if project_dir.exists() and any(project_dir.iterdir()):
        raise ScaffoldError(strings.ERROR_TARGET_NOT_EMPTY.format(project_dir=project_dir))


def validate_scaffold_name(scaffold: str) -> None:
    """Refuse to copy from a scaffold that isn't bundled. No filesystem writes."""
    source = SCAFFOLDS_DIR / scaffold
    if not source.is_dir():
        available = ", ".join(sorted(p.name for p in SCAFFOLDS_DIR.iterdir() if p.is_dir()))
        raise ScaffoldError(
            strings.ERROR_UNKNOWN_SCAFFOLD.format(
                scaffold=scaffold,
                available=available or strings.HINT_NONE,
            )
        )


def validate_scaffold_target(project_dir: Path, *, scaffold: str) -> None:
    """Combined target-dir + scaffold-name validation. No filesystem writes."""
    validate_scaffold_name(scaffold)
    validate_target_dir(project_dir)


def validate_agent(*, scaffold: str, agent: str) -> None:
    """Refuse to assemble an agent the scaffold doesn't vendor. No filesystem writes."""
    agents_dir = SCAFFOLDS_DIR / scaffold / PER_AGENT_DIR
    if not (agents_dir / agent).is_dir():
        available = ", ".join(sorted(p.name for p in agents_dir.iterdir() if p.is_dir())) if agents_dir.is_dir() else ""
        raise ScaffoldError(
            strings.ERROR_UNKNOWN_AGENT.format(
                agent=agent,
                scaffold=scaffold,
                available=available or strings.HINT_NONE,
            )
        )


def copy_scaffold(project_dir: Path, *, scaffold: str, agent: str | None = None) -> None:
    """Copy the bundled scaffold into ``project_dir``.

    Lays down the scaffold's shared source, then overlays the selected agent's
    vendored AI files from ``_agents/<agent>/``. Pass ``agent=None`` to copy
    only the shared source (useful for tests that just want the base layout).
    """
    validate_scaffold_target(project_dir, scaffold=scaffold)
    source = SCAFFOLDS_DIR / scaffold
    if agent is not None:
        validate_agent(scaffold=scaffold, agent=agent)

    def _ignore_shared(src: str, names: list[str]) -> set[str]:
        # The per-agent trees are overlaid selectively below, never copied wholesale.
        skip = _ignore_runtime(src, names)
        if Path(src) == source and PER_AGENT_DIR in names:
            skip.add(PER_AGENT_DIR)
        return skip

    project_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, project_dir, ignore=_ignore_shared, dirs_exist_ok=True)

    if agent is not None:
        shutil.copytree(source / PER_AGENT_DIR / agent, project_dir, dirs_exist_ok=True)

    _stamp_install_time(project_dir)


def _stamp_install_time(project_dir: Path) -> None:
    """Replace the sentinel `installed_at` in the toolkits manifest with now."""
    manifest = project_dir / TOOLKITS_MANIFEST
    if not manifest.exists():
        return
    content = manifest.read_text(encoding="utf-8")
    if INSTALL_TIME_SENTINEL not in content:
        return
    now_iso = datetime.now(timezone.utc).isoformat()
    manifest.write_text(content.replace(INSTALL_TIME_SENTINEL, now_iso), encoding="utf-8")


def _ignore_runtime(src: str, names: list[str]) -> set[str]:
    """Skip dev-time artifacts that may sit alongside the scaffold sources."""
    skip: set[str] = set()
    src_basename = Path(src).name

    for name in names:
        if name in {"__pycache__", ".venv", ".pytest_cache", ".ruff_cache", ".mypy_cache"}:
            skip.add(name)
        elif name.endswith(".pyc"):
            skip.add(name)
        elif src_basename == ".dlt" and name in {"data", "state", ".var"}:
            skip.add(name)

    return skip
