"""Project-wide constants for the `dlthub-start` CLI."""

from __future__ import annotations

from dataclasses import dataclass

VERSION = "0.5.0"

SCAFFOLDS = (
    (
        "minimal_workspace",
        "Minimal",
        "a local dltHub workspace with a single dlt pipeline: for a quick look how dltHub Pro works.",
    ),
    (
        "starter_workspace",
        "Starter",
        "the full local dltHub workspace experience: agentic ingestion, transformations, data quality, and notebooks.",
    ),
)

AGENTS = ("claude", "cursor", "codex")

# Fallback workspace name when a user runs `dlthub-start --yes` (or accepts
# the project-name prompt without typing anything).
DEFAULT_PROJECT_NAME = "my-workspace"

TOOLKITS = (
    "data-exploration",
    "dlthub-platform",
    "rest-api-pipeline",
)

# Pinned commit of dlt-hub/dlthub-ai-workbench that `make generate-ai` fetches.
# Setting a SHA keeps generation reproducible across machines and over time:
# CI's `check-ai` step compares the committed scaffold against whatever this
# ref produces, so any drift becomes a deliberate two-line PR (bump SHA +
# commit regenerated scaffold).
#
# To bump: pick a new SHA (the workbench repo has no tags today), update the
# constant below, run `make generate-ai`, commit the resulting scaffold diff
# alongside this change.
WORKBENCH_REF: str | None = "c42500573e979fa85e274502edd2cb0d2019ecaf"


@dataclass(frozen=True)
class RecommendedPath:
    """The path we recommend new users follow. Also the path `--yes` runs."""

    scaffold: str
    install_uv: bool
    run_uv_sync: bool
    agents: tuple[str, ...]


RECOMMENDED = RecommendedPath(
    scaffold="minimal_workspace",
    install_uv=True,
    run_uv_sync=True,
    agents=AGENTS,
)
