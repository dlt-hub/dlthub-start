"""Project-wide constants for the `dlthub-start` CLI."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version

DISTRIBUTION_NAME = "dlthub-start"

try:
    VERSION = version(DISTRIBUTION_NAME)
except PackageNotFoundError:
    VERSION = "0.0.0+unknown"

GITHUB_ORG = "dlt-hub"

AGENTS = ("claude", "codex", "cursor")

AGENT_LAUNCH_COMMANDS = {
    "claude": ("claude",),
    "codex": ("codex",),
}

# Per-agent skills directory, relative to the workspace root (validated against the
# generated scaffold in test_config). Used to show where the entry skill lives.
AGENT_SKILLS_DIR = {
    "claude": ".claude/skills",
    "codex": ".agents/skills",
    "cursor": ".cursor/skills",
}

# Name of the platform workspace the first pipeline run binds the project to.
# A binding only (no destination) — the warehouse still comes from the profile.
# Adjust here to rename it everywhere (CLI command + user-facing messages).
PLAYGROUND_WORKSPACE = "playground"

TOOLKITS = ("one-shot",)

# Workflow entry skill of the one-shot toolkit. The non-TTY handoff points the calling
# agent at it; test_config asserts it exists in the generated scaffold so it can't drift.
ONE_SHOT_ENTRY_SKILL = "deploy-run-sample-pipeline"

# The dltHub AI workbench repo that `make generate-ai` / `make update-ai` pull from.
WORKBENCH_REPO_NAME = "dlthub-ai-workbench"
WORKBENCH_REPO = f"https://github.com/{GITHUB_ORG}/{WORKBENCH_REPO_NAME}.git"

# Pinned commit of dlt-hub/dlthub-ai-workbench that `make generate-ai` fetches.
# Setting a SHA keeps generation reproducible across machines and over time:
# CI's `check-ai` step compares the committed scaffold against whatever this
# ref produces, so any drift becomes a deliberate two-line PR (bump SHA +
# commit regenerated scaffold).
#
# To bump: pick a new SHA (the workbench repo has no tags today), update the
# constant below, run `make generate-ai`, commit the resulting scaffold diff
# alongside this change.
# WORKBENCH_REF: str | None = "1853f504a88d018c9d47f62bcbdfa43aa3384a35"
WORKBENCH_REF: str | None = "feat/handover-after-onboarding"


@dataclass(frozen=True)
class RecommendedPath:
    """The path we recommend new users follow. Also the path `--setup-only` runs."""

    scaffold: str
    install_uv: bool
    agent: str


RECOMMENDED = RecommendedPath(
    scaffold="minimal_workspace",
    install_uv=True,
    agent="claude",
)
