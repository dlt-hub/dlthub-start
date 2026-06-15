"""Project-wide constants for the `dlthub-start` CLI."""

from __future__ import annotations

from dataclasses import dataclass

VERSION = "0.7.0"

AGENTS = ("claude", "codex", "cursor")

AGENT_LAUNCH_COMMANDS = {
    "claude": ("claude",),
    "codex": ("codex",),
}

# Name of the platform workspace the first pipeline run binds the project to.
# A binding only (no destination) — the warehouse still comes from the profile.
# Adjust here to rename it everywhere (CLI command + user-facing messages).
PLAYGROUND_WORKSPACE = "playground"

TOOLKITS = ("one-shot")

# The dltHub AI workbench repo that `make generate-ai` / `make update-ai` pull from.
WORKBENCH_REPO = "https://github.com/dlt-hub/dlthub-ai-workbench.git"

# Pinned commit of dlt-hub/dlthub-ai-workbench that `make generate-ai` fetches.
# Setting a SHA keeps generation reproducible across machines and over time:
# CI's `check-ai` step compares the committed scaffold against whatever this
# ref produces, so any drift becomes a deliberate two-line PR (bump SHA +
# commit regenerated scaffold).
#
# To bump: pick a new SHA (the workbench repo has no tags today), update the
# constant below, run `make generate-ai`, commit the resulting scaffold diff
# alongside this change.
WORKBENCH_REF: str | None = "eeacfb8acfe8990989f1c38da37e5e7e5b335eee"


@dataclass(frozen=True)
class RecommendedPath:
    """The path we recommend new users follow. Also the path `--yes` runs."""

    scaffold: str
    install_uv: bool
    agent: str


RECOMMENDED = RecommendedPath(
    scaffold="minimal_workspace",
    install_uv=True,
    agent="claude",
)
