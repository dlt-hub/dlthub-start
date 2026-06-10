"""Project-wide constants for the `dlthub-start` CLI."""

from __future__ import annotations

from dataclasses import dataclass

VERSION = "0.5.3"

AGENTS = ("claude", "cursor", "codex")

TOOLKITS = (
    "one-shot-pipeline"
)

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
WORKBENCH_REF: str | None = "21b9bba4ee3fb2f472cace5e97bf8df6679d54ba"


@dataclass(frozen=True)
class RecommendedPath:
    """The path we recommend new users follow. Also the path `--yes` runs."""

    scaffold: str
    install_uv: bool
    run_uv_sync: bool
    agent: str


RECOMMENDED = RecommendedPath(
    scaffold="minimal_workspace",
    install_uv=True,
    run_uv_sync=True,
    agent="claude",
)
