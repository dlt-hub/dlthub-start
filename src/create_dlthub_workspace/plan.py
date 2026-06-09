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
from .prompts import choose_agent, choose_scaffold, confirm
from .scaffold import validate_agent, validate_scaffold_name, validate_target_dir
from .uv import find_uv


class WorkspaceStage(Enum):
    """How far the execution phase should run before stopping."""

    SCAFFOLD_ONLY = "scaffold_only"
    THROUGH_UV_INSTALL = "through_uv_install"
    FULL = "full"


@dataclass(frozen=True)
class WorkspacePlan:
    project_dir: Path
    scaffold: str
    stage: WorkspaceStage
    agent: str
    uv_executable: str | None
    install_uv: bool
    verbose: bool


def build_plan(args: argparse.Namespace) -> WorkspacePlan:
    """Gather every answer needed to scaffold the workspace. No filesystem writes.

    Order: target -> scaffold -> agents (content questions), then uv install
    + sync (setup questions). The target-directory check fires first so an
    occupied directory fails fast — before the user answers any other questions.

    The workspace is initialized in place: the current directory by default, or
    an explicit ``project_dir`` if given. Either way the target must be empty.
    """
    project_dir = (Path(args.project_dir).expanduser() if args.project_dir else Path.cwd()).resolve()
    validate_target_dir(project_dir)

    scaffold = args.scaffold or (RECOMMENDED.scaffold if args.yes else choose_scaffold())
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

    if stage != WorkspaceStage.SCAFFOLD_ONLY:
        if args.skip_uv_sync or (
            not args.yes
            and not confirm(
                strings.PROMPT_RUN_UV_SYNC,
                recommended=RECOMMENDED.run_uv_sync,
            )
        ):
            stage = WorkspaceStage.THROUGH_UV_INSTALL

    return WorkspacePlan(
        project_dir=project_dir,
        scaffold=scaffold,
        stage=stage,
        agent=agent,
        uv_executable=uv_executable,
        install_uv=install_uv,
        verbose=args.verbose,
    )
