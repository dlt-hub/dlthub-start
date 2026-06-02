"""Regenerate bundled AI workbench files in every scaffold, one agent at a time.

Run via `make generate-ai`. For each scaffold, for each agent:

1. Copy the scaffold's shared source (minus runtime artifacts and any existing
   AI files) to a throwaway tmp dir.
2. `uv sync` so `dlthub` is on PATH inside that workspace.
3. Run `dlthub ai init --agent <agent>` and `dlthub ai toolkit install` for
   each TOOLKIT, pinning to `WORKBENCH_REF` from config.py.
4. Mirror the toolkit skills into the agent's own skill dir (claude/cursor).
5. Capture that agent's AI-generated entries into
   `scaffolds/<scaffold>/_agents/<agent>/` — each agent gets its OWN
   self-contained set, including its own `.dlt/.toolkits` manifest.

`copy_scaffold` then lays down the shared source plus exactly one agent's
`_agents/<agent>/` tree at scaffold time. Commit the resulting diff alongside
any `WORKBENCH_REF` bump.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from create_dlthub_workspace.config import AGENTS, TOOLKITS, WORKBENCH_REF  # noqa: E402
from create_dlthub_workspace.scaffold import (  # noqa: E402
    INSTALL_TIME_SENTINEL,
    PER_AGENT_DIR,
    SCAFFOLDS_DIR,
    TOOLKITS_MANIFEST,
)

_INSTALLED_AT_RE = re.compile(r"installed_at: '[^']*'")

# Top-level entries (relative to the workspace root) that `dlthub ai init` /
# `toolkit install` produce. Captured per agent into `_agents/<agent>/`.
# Anything not in this set is scaffold source code (pipelines, pyproject.toml,
# .dlt/config.toml, etc.) and stays shared at the scaffold root.
AI_GENERATED_ENTRIES: tuple[str, ...] = (
    ".agents",
    ".claude",
    ".claudeignore",
    ".cursor",
    ".cursorignore",
    ".codex",
    ".codexignore",
    "AGENTS.md",
    ".mcp.json",
    ".dlt/.toolkits",
)

_RUNTIME_DIRS = {".venv", ".pytest_cache", ".ruff_cache", ".mypy_cache", "__pycache__"}


def _ignore_runtime(src: str, names: list[str]) -> set[str]:
    """Skip dev-time artifacts when seeding the throwaway workspace."""
    skip: set[str] = set()
    src_basename = Path(src).name
    for name in names:
        if name in _RUNTIME_DIRS or name.endswith(".pyc"):
            skip.add(name)
        elif src_basename == ".dlt" and name in {"data", "state", ".var"}:
            skip.add(name)
    return skip


def _isolated_env() -> dict[str, str]:
    """Drop parent venv hints so uv resolves the workspace's own .venv."""
    env = os.environ.copy()
    for name in ("VIRTUAL_ENV", "CONDA_PREFIX", "PYTHONPATH"):
        env.pop(name, None)
    return env


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, env=_isolated_env(), check=True)


def _mirror_agent_skills(work: Path) -> None:
    """Copy each skill from .agents/skills/ into .claude/skills/ and .cursor/skills/.

    Upstream `dlthub ai init` only seeds the core always-on skills into Claude
    and Cursor's dedicated skill dirs, expecting agents to discover the rest
    via .agents/. But Claude and Cursor only auto-discover skills inside their
    own dirs, so toolkit skills become invisible to them. Mirror them so both
    agents see the full set. Skip-if-exists preserves the core skills already
    placed there by `dlthub ai init`.

    Per-agent runs only have one of .claude/.cursor present, so this naturally
    targets just the agent being generated.
    """
    source = work / ".agents" / "skills"
    if not source.is_dir():
        return
    for target_root in (work / ".claude" / "skills", work / ".cursor" / "skills"):
        if not target_root.is_dir():
            continue
        for skill_dir in sorted(source.iterdir()):
            if not skill_dir.is_dir():
                continue
            dest = target_root / skill_dir.name
            if dest.exists():
                continue
            shutil.copytree(skill_dir, dest)


def _branch_args() -> list[str]:
    """Render --branch only when a ref is pinned; otherwise let dlthub use upstream default."""
    return ["--branch", WORKBENCH_REF] if WORKBENCH_REF else []


def _capture_ai_entries(work: Path, dest_root: Path) -> None:
    """Copy the AI-generated entries from a generated workspace into dest_root."""
    for entry in AI_GENERATED_ENTRIES:
        source = work / entry
        if not source.exists():
            continue
        target = dest_root / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)


def regenerate(scaffold_dir: Path) -> None:
    print(f"\n=== {scaffold_dir.name} ===")

    # Clear any previously generated AI output: the old merged root entries
    # (pre per-agent layout) and the per-agent tree itself.
    for entry in AI_GENERATED_ENTRIES:
        _remove(scaffold_dir / entry)
    _remove(scaffold_dir / PER_AGENT_DIR)

    ref_label = WORKBENCH_REF or "<upstream default>"

    for agent in AGENTS:
        print(f"  --- agent: {agent} ---")
        with tempfile.TemporaryDirectory(prefix=f"gen-ai-{scaffold_dir.name}-{agent}-") as tmp:
            work = Path(tmp) / "workspace"
            shutil.copytree(scaffold_dir, work, ignore=_ignore_runtime)
            # Never carry a previously-generated agent's output into this run.
            _remove(work / PER_AGENT_DIR)

            print("    uv sync")
            _run(["uv", "sync"], cwd=work)

            print(f"    dlthub ai init --agent {agent}  (ref={ref_label})")
            _run(
                [
                    "uv",
                    "run",
                    "dlthub",
                    "--non-interactive",
                    "ai",
                    "init",
                    "--agent",
                    agent,
                    *_branch_args(),
                    "--overwrite",
                ],
                cwd=work,
            )

            for toolkit in TOOLKITS:
                print(f"    dlthub ai toolkit install {toolkit}  (ref={ref_label})")
                _run(
                    [
                        "uv",
                        "run",
                        "dlthub",
                        "--non-interactive",
                        "ai",
                        "toolkit",
                        "install",
                        toolkit,
                        *_branch_args(),
                        "--overwrite",
                    ],
                    cwd=work,
                )

            print("    mirror .agents/skills -> .claude/skills, .cursor/skills")
            _mirror_agent_skills(work)

            dest_root = scaffold_dir / PER_AGENT_DIR / agent
            _capture_ai_entries(work, dest_root)
            _normalize_install_time(dest_root / TOOLKITS_MANIFEST)

    print("  done")


def _normalize_install_time(manifest: Path) -> None:
    """Replace dynamic `installed_at` timestamps with a fixed sentinel.

    Keeps `check-ai` diffs clean across machines; copy_scaffold restores a
    real UTC timestamp when a user actually creates a workspace.
    """
    if not manifest.exists():
        return
    content = manifest.read_text(encoding="utf-8")
    content = _INSTALLED_AT_RE.sub(f"installed_at: '{INSTALL_TIME_SENTINEL}'", content)
    manifest.write_text(content, encoding="utf-8")


def main() -> int:
    print(f"Regenerating AI workbench files per agent (WORKBENCH_REF={WORKBENCH_REF})")
    for scaffold_dir in sorted(p for p in SCAFFOLDS_DIR.iterdir() if p.is_dir()):
        regenerate(scaffold_dir)
    print("\nAll scaffolds refreshed. Review with `git diff src/create_dlthub_workspace/scaffolds/`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
