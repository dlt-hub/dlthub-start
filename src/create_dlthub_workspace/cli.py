"""Command-line entrypoint for the `dlthub-start` CLI."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from . import strings
from .config import AGENT_LAUNCH_COMMANDS, AGENTS, RECOMMENDED
from .display import (
    console,
    copy_to_clipboard,
    err_console,
    print_banner,
    print_created_tree,
    print_dir_not_empty,
    print_next_steps,
    print_resume_steps,
    substep,
    substep_detail,
)
from .errors import WorkspaceDirectoryNotEmptyError, WorkspaceError
from .project_metadata import apply_workspace_name
from .prompts import choose_agent, confirm, stdin_is_interactive
from .scaffold import (
    copy_scaffold,
    overlay_agent,
    resolve_workspace_target,
    validate_agent,
    validate_scaffold_name,
)
from .uv import execute_uv_install, find_uv, run_uv_sync


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
        description=(
            "Create a dltHub workspace and run a guided first experience — scaffold, "
            "install, run a sample pipeline, and open your coding agent."
        ),
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=None,
        help=(
            "Directory to scaffold into. Defaults to the current directory, falling back to "
            "a ./playground subdirectory (then ./playground-N) when it isn't empty. An explicit "
            "name that's occupied falls back to <name>-1, <name>-2, …"
        ),
    )
    parser.add_argument(
        "--agent",
        choices=AGENTS,
        help=f"Coding agent to set up ({', '.join(AGENTS)}). If omitted, you'll be prompted to choose (default: {RECOMMENDED.agent}).",
    )
    # Hidden, non-interactive shortcut for tests/CI only. Absent from --help so the
    # interactive flow is the sole documented path. See MSG_TESTING_SHORTCUT_NOTE.
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Stream output from underlying subprocesses (uv, dlthub).",
    )
    # Hidden, like --yes: a non-interactive shortcut for tests/CI that stops
    # before dependency sync (and, with it, the guided first run), leaving an
    # incomplete workspace. Kept functional but absent from --help so the
    # interactive flow is the sole documented path. See MSG_TESTING_SHORTCUT_NOTE.
    parser.add_argument(
        "--skip-uv-sync",
        action="store_true",
        help=argparse.SUPPRESS,
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
    except WorkspaceDirectoryNotEmptyError as exc:
        print_dir_not_empty(exc.project_dir)
        return 2
    except WorkspaceError as exc:
        console.print(strings.MSG_ERROR_PREFIX.format(message=exc))
        return 1
    except Exception as exc:
        console.print(strings.MSG_UNEXPECTED_ERROR.format(message=exc))
        if args.verbose:
            console.print_exception()
        else:
            console.print(strings.MSG_UNEXPECTED_ERROR_HINT)
        return 1
    return 0


def run(args: argparse.Namespace) -> None:
    # Banner is decorative — skip it in non-TTY runs where it's just log noise.
    if stdin_is_interactive():
        print_banner()
        console.print()

    if args.yes or args.skip_uv_sync:
        err_console.print(strings.MSG_TESTING_SHORTCUT_NOTE)

    verbose = args.verbose
    scaffold = RECOMMENDED.scaffold
    validate_scaffold_name(scaffold)
    if args.agent is not None:
        validate_agent(scaffold=scaffold, agent=args.agent)

    resolution = resolve_workspace_target(args.project_dir)
    project_dir = resolution.project_dir
    if resolution.relocated_from is not None:
        console.print(strings.MSG_RELOCATED.format(relocated_from=resolution.relocated_from, project_dir=project_dir))

    with substep(
        strings.MSG_CREATING_WORKSPACE.format(project_dir=project_dir),
        strings.MSG_CREATED.format(project_dir=project_dir),
        verbose=verbose,
    ):
        copy_scaffold(project_dir, scaffold=scaffold, agent=None)
        package_name = apply_workspace_name(project_dir, project_dir.name)
    substep_detail(strings.MSG_PACKAGE_NAME.format(package_name=package_name))
    print_created_tree(scaffold)

    uv_executable = find_uv()
    if uv_executable is None:
        if args.yes or confirm(strings.PROMPT_INSTALL_UV, recommended=RECOMMENDED.install_uv):
            uv_executable = execute_uv_install(verbose=verbose)
        else:
            _finalize_agent(project_dir, scaffold, args, verbose=verbose)
            console.print(strings.MSG_SKIPPED_UV_AND_SYNC)
            print_resume_steps(project_dir, uv_installed=False)
            return

    if args.skip_uv_sync:
        _finalize_agent(project_dir, scaffold, args, verbose=verbose)
        console.print(strings.MSG_SKIPPED_SYNC)
        print_resume_steps(project_dir, uv_installed=True)
        return

    with substep(strings.MSG_INSTALLING_DEPS, strings.MSG_INSTALLED_DEPS, verbose=verbose):
        run_uv_sync(uv_executable, project_dir, verbose=verbose)

    agent = _finalize_agent(project_dir, scaffold, args, verbose=verbose)
    console.print(strings.MSG_INVOKE_SKILL)

    if not args.yes and _launch_agent(project_dir, agent, prompt=strings.CMD_BUILD_OWN_SOURCE_PROMPT):
        return

    console.print()
    prompt_copied = not args.yes and copy_to_clipboard(strings.CMD_BUILD_OWN_SOURCE_PROMPT)
    print_next_steps(project_dir, scaffold=scaffold, first_pipeline_ran=not args.yes, prompt_copied=prompt_copied)


def _finalize_agent(project_dir: Path, scaffold: str, args: argparse.Namespace, *, verbose: bool) -> str:
    """Resolve the agent (prompting unless --agent/--yes set it) and lay down its AI files."""
    agent = args.agent or (RECOMMENDED.agent if args.yes else choose_agent())
    with substep(
        strings.MSG_ADDING_AGENT_FILES.format(agent=agent),
        strings.MSG_ADDED_AGENT_FILES.format(agent=agent),
        verbose=verbose,
    ):
        overlay_agent(project_dir, scaffold=scaffold, agent=agent)
    return agent


def _launch_agent(project_dir: Path, agent: str, *, prompt: str) -> bool:
    """Launch ``agent`` in the workspace, seeded with ``prompt``; False if it has no
    terminal CLI on PATH, so the caller falls back to the clipboard panel."""
    base = AGENT_LAUNCH_COMMANDS.get(agent)
    if base is None:
        return False
    executable = shutil.which(base[0])
    if executable is None:
        return False
    console.print(strings.MSG_LAUNCHING_AGENT.format(agent=agent))
    try:
        subprocess.run([executable, *base[1:], prompt], cwd=project_dir, check=False)
    except OSError:
        return False
    return True


if __name__ == "__main__":
    sys.exit(main())
