"""Command-line entrypoint for the `dlthub-start` CLI."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import strings
from .config import AGENT_LAUNCH_COMMANDS, AGENTS, PLAYGROUND_WORKSPACE, RECOMMENDED
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
    substep_streaming,
)
from .errors import UvError, WorkspaceDirectoryNotEmptyError, WorkspaceError
from .project_metadata import apply_workspace_name
from .prompts import choose_agent, confirm, stdin_is_interactive
from .scaffold import (
    copy_scaffold,
    overlay_agent,
    resolve_workspace_target,
    validate_agent,
    validate_scaffold_name,
)
from .uv import capture_uv_command, execute_uv_install, find_uv, run_uv_command, run_uv_sync


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

    # Skipped under --yes: the first run's login is interactive. A run that exits
    # non-zero degrades to a warning so the rest of setup still completes.
    # LIMITATION: `dlthub run --follow` can exit 0 on a failed remote run, so a
    # genuine run failure isn't caught here — we'd still report success. Revisit.
    first_pipeline_ran = not args.yes
    if first_pipeline_ran:
        try:
            _run_first_pipeline(uv_executable, project_dir, verbose=verbose)
            console.print(strings.MSG_PLAYGROUND_READY)
        except UvError as exc:
            first_pipeline_ran = False
            console.print(strings.MSG_FIRST_RUN_FAILED.format(message=exc))

    agent = _finalize_agent(project_dir, scaffold, args, verbose=verbose)

    if first_pipeline_ran and _launch_agent(project_dir, agent, prompt=strings.CMD_BUILD_OWN_SOURCE_PROMPT):
        return

    console.print()
    prompt_copied = first_pipeline_ran and copy_to_clipboard(strings.CMD_BUILD_OWN_SOURCE_PROMPT)
    print_next_steps(project_dir, scaffold=scaffold, first_pipeline_ran=first_pipeline_ran, prompt_copied=prompt_copied)


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


def _run_first_pipeline(uv_executable: str, project_dir: Path, *, verbose: bool) -> None:
    """Log in, bind the playground workspace, run load_sample_shop, show the run."""
    # Login is the only interactive step, so stream it; it also authenticates the steps below.
    with substep_streaming(strings.MSG_LOGGING_IN, strings.MSG_LOGGED_IN):
        run_uv_command(uv_executable, project_dir, ["run", "dlthub", "login"], verbose=True)

    with substep(
        strings.MSG_CONNECTING_PLAYGROUND.format(workspace=PLAYGROUND_WORKSPACE),
        strings.MSG_CONNECTED_PLAYGROUND.format(workspace=PLAYGROUND_WORKSPACE),
        verbose=verbose,
    ):
        # connect --create errors on an existing workspace, so pass it only when absent.
        connect_args = ["run", "dlthub", "workspace", "connect", PLAYGROUND_WORKSPACE]
        if not _playground_exists(uv_executable, project_dir):
            connect_args.append("--create")
        run_uv_command(uv_executable, project_dir, connect_args, verbose=verbose)

    # No --follow: submit the run without blocking/streaming; the show step below surfaces its logs.
    # with substep(strings.MSG_RUNNING_FIRST_PIPELINE, strings.MSG_RAN_FIRST_PIPELINE, verbose=verbose):
    #     run_uv_command(
    #         uv_executable,
    #         project_dir,
    #         ["run", "dlthub", "run", "load_sample_shop"],
    #         verbose=verbose,
    #     )

    # with substep(strings.MSG_SHOWING_RUN, strings.MSG_SHOWED_RUN, verbose=verbose):
    #     run_uv_command(
    #         uv_executable,
    #         project_dir,
    #         ["run", "dlthub", "job", "runs", "show", "pipeline.load_sample_shop"],
    #         verbose=verbose,
    #     )


def _workspace_in_list(list_output: str, name: str) -> bool:
    """True if ``name`` appears in the Name column of `dlthub workspace list`.

    The output is a space-padded table; workspace names can contain single
    spaces (e.g. "My Workspace"), so columns are split on runs of 2+ spaces and
    the first field is the name. The header row (before the dashed separator)
    and the separator itself are skipped, so a workspace literally named like a
    column header can't false-match.
    """
    seen_separator = False
    for line in list_output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if set(stripped) <= {"-", " "}:
            seen_separator = True
            continue
        if not seen_separator:
            continue  # header row(s) above the separator
        first_column = re.split(r"\s{2,}", stripped)[0]
        if first_column == name:
            return True
    return False


def _playground_exists(uv_executable: str, project_dir: Path) -> bool:
    """Report whether the playground workspace already exists for the user.

    Lists remote workspaces with --non-interactive so an unauthenticated user
    fails fast (no hanging prompt) instead of blocking. On any failure we report
    False, so the caller falls back to `connect --create` — and that connect
    step then triggers the interactive login.
    """
    try:
        output = capture_uv_command(
            uv_executable,
            project_dir,
            ["run", "dlthub", "--non-interactive", "workspace", "list"],
        )
    except UvError:
        return False
    return _workspace_in_list(output, PLAYGROUND_WORKSPACE)


if __name__ == "__main__":
    sys.exit(main())
