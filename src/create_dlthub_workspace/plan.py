"""Resolved answers to every question the CLI asks the user.

A `WorkspacePlan` is built once during the planning phase and then frozen.
Execution reads from it and must not prompt the user again.

Auto-detection (uv presence, target-dir validity, scaffold availability) runs
in `build_plan` BEFORE the related prompt fires.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from . import strings
from .config import RECOMMENDED
from .prompts import choose_agent, confirm
from .scaffold import resolve_workspace_target, validate_agent, validate_scaffold_name
from .uv import find_uv


class WorkspaceStage(Enum):
    """How far the execution phase should run before stopping."""

    SCAFFOLD_ONLY = "scaffold_only"
    THROUGH_UV_INSTALL = "through_uv_install"
    FULL = "full"


@dataclass(frozen=True)
class WorkspacePlan:
    project_dir: Path
    relocated_from: Path | None
    scaffold: str
    stage: WorkspaceStage
    agent: str
    uv_executable: str | None
    install_uv: bool
    run_first_pipeline: bool
    verbose: bool


def build_plan(args: argparse.Namespace) -> WorkspacePlan:
    """Gather every answer needed to scaffold the workspace. No filesystem writes.

    Order: target -> agent (content question), then the uv-install question (only
    when uv is missing). The target-directory check fires first so an occupied
    directory fails fast. There is a single bundled scaffold, so no scaffold
    prompt is asked. uv sync and the first pipeline run happen automatically:
    --skip-uv-sync opts out of sync, and the first run is skipped under --yes
    (its login is interactive).

    The workspace is initialized in place when the target is empty: the current
    directory by default, or an explicit ``project_dir`` if given. An occupied
    target never fails — it falls back to a free directory (a ``playground``
    subdirectory for the default, or a ``name-1``/``name-2`` sibling for an
    explicit name), recorded as ``relocated_from`` so the user is told where it
    landed.
    """
    resolution = resolve_workspace_target(args.project_dir)
    project_dir = resolution.project_dir

    scaffold = RECOMMENDED.scaffold
    validate_scaffold_name(scaffold)

    agent = args.agent or (RECOMMENDED.agent if args.yes else choose_agent())
    validate_agent(scaffold=scaffold, agent=agent)

    uv_executable = find_uv()
    install_uv = False
    stage = WorkspaceStage.FULL

    if uv_executable is None:
        if args.yes or confirm(
            strings.PROMPT_INSTALL_UV,
            recommended=RECOMMENDED.install_uv,
        ):
            install_uv = True
        else:
            stage = WorkspaceStage.SCAFFOLD_ONLY

    # uv sync runs automatically; --skip-uv-sync is the explicit opt-out.
    if stage is WorkspaceStage.FULL and args.skip_uv_sync:
        stage = WorkspaceStage.THROUGH_UV_INSTALL

    # Run the first pipeline automatically once deps are in place (stage FULL).
    # Never under --yes: the first run triggers an interactive login that a
    # non-interactive invocation can't answer.
    run_first_pipeline = stage is WorkspaceStage.FULL and not args.yes

    return WorkspacePlan(
        project_dir=project_dir,
        relocated_from=resolution.relocated_from,
        scaffold=scaffold,
        stage=stage,
        agent=agent,
        uv_executable=uv_executable,
        install_uv=install_uv,
        run_first_pipeline=run_first_pipeline,
        verbose=args.verbose,
    )
