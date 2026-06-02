"""Command-line entrypoint for the `dlthub-start` CLI."""

from __future__ import annotations

import argparse
import sys

from . import strings
from .config import AGENTS, RECOMMENDED, SCAFFOLDS
from .display import console, print_banner, print_next_steps, print_resume_steps, step
from .errors import WorkspaceError
from .plan import WorkspacePlan, WorkspaceStage, build_plan
from .project_metadata import apply_workspace_name
from .scaffold import copy_scaffold
from .uv import execute_uv_install, run_uv_sync


def _ensure_utf8_io_on_windows() -> None:
    """Force UTF-8 on stdio when running on Windows.

    The banner uses full-block characters (`█`, U+2588) that can't be encoded
    by Windows' default cp1252 codec. This bites in two places: legacy
    cmd.exe terminals, and when stdout is piped (subprocess capture, CI
    log collection). Reconfiguring before rich.Console writes anything keeps
    the output portable.
    """
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dlthub-start",
        description="Scaffold a new dltHub workspace.",
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=None,
        help="Directory to create for the new workspace. Prompts if omitted.",
    )
    parser.add_argument(
        "--scaffold",
        choices=[key for key, _, _ in SCAFFOLDS],
        help=f"Bundled scaffold to use. Defaults to the recommended {RECOMMENDED.scaffold!r} in non-interactive mode.",
    )
    parser.add_argument(
        "--agent",
        choices=AGENTS,
        help=f"Coding agent to set up. Defaults to the recommended {RECOMMENDED.agent!r} in non-interactive mode.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help=f"Run the recommended path (minimal scaffold, install uv, uv sync, {RECOMMENDED.agent} agent).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Stream output from underlying subprocesses (uv, dlthub).",
    )
    parser.add_argument(
        "--skip-uv-sync",
        action="store_true",
        help="Stop before dependency sync. The scaffold and selected agent's files are still created.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_io_on_windows()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        run(args)
    except KeyboardInterrupt:
        console.print(strings.MSG_CANCELLED)
        return 130
    except WorkspaceError as exc:
        console.print(strings.MSG_ERROR_PREFIX.format(message=exc))
        return 1
    return 0


def run(args: argparse.Namespace) -> None:
    print_banner()
    console.print()

    plan = build_plan(args)
    execute_plan(plan)


def execute_plan(plan: WorkspacePlan) -> None:
    verbose = plan.verbose

    with step(strings.MSG_CREATING_WORKSPACE.format(project_dir=plan.project_dir), verbose=verbose):
        copy_scaffold(plan.project_dir, scaffold=plan.scaffold, agent=plan.agent)
        package_name = apply_workspace_name(plan.project_dir, plan.project_dir.name)
    console.print(strings.MSG_CREATED.format(project_dir=plan.project_dir))
    console.print(strings.MSG_PACKAGE_NAME.format(package_name=package_name))

    if plan.stage is WorkspaceStage.SCAFFOLD_ONLY:
        console.print(strings.MSG_SKIPPED_UV_AND_SYNC)
        print_resume_steps(plan.project_dir, uv_installed=False)
        return

    if plan.install_uv:
        uv_executable = execute_uv_install(verbose=verbose)
    else:
        assert plan.uv_executable is not None
        uv_executable = plan.uv_executable

    if plan.stage is WorkspaceStage.THROUGH_UV_INSTALL:
        console.print(strings.MSG_SKIPPED_SYNC)
        print_resume_steps(plan.project_dir, uv_installed=True)
        return

    with step(strings.MSG_INSTALLING_DEPS, verbose=verbose):
        run_uv_sync(uv_executable, plan.project_dir, verbose=verbose)
    console.print(strings.MSG_INSTALLED_DEPS)

    console.print()
    print_next_steps(plan.project_dir, scaffold=plan.scaffold, agent=plan.agent)


if __name__ == "__main__":
    sys.exit(main())
