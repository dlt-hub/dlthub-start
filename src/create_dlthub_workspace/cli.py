"""Command-line entrypoint for the `dlthub-start` CLI."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from . import strings, telemetry
from .config import (
    AGENT_LAUNCH_COMMANDS,
    AGENT_SKILLS_DIR,
    AGENTS,
    DISTRIBUTION_NAME,
    ONE_SHOT_ENTRY_SKILL,
    PLAYGROUND_WORKSPACE,
    RECOMMENDED,
)
from .display import (
    console,
    copy_to_clipboard,
    err_console,
    print_banner,
    print_created_tree,
    print_dir_not_empty,
    print_error,
    print_launch_plan,
    print_next_steps,
    print_verbatim,
    substep,
    substep_detail,
)
from .errors import UvError, WorkspaceDirectoryNotEmptyError, WorkspaceError
from .project_metadata import apply_dlthub_client_source, apply_runtime_base_urls, apply_workspace_name
from .prompts import choose_agent, confirm, stdin_is_interactive
from .scaffold import (
    copy_scaffold,
    overlay_agent,
    resolve_workspace_target,
    validate_agent,
    validate_scaffold_name,
)
from .uv import execute_uv_install, find_uv, run_uv_command, run_uv_sync


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
        prog=DISTRIBUTION_NAME,
        description=(
            "Create a dltHub workspace and hand off to your coding agent — scaffold, install, "
            "log in, and connect a playground, then the agent deploys and runs the sample pipeline."
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
    parser.add_argument(
        "--api-base-url",
        metavar="URL",
        default=None,
        help="Point the workspace at a non-prod dltHub runtime by writing api_base_url into .dlt/config.toml at scaffold time (omit for prod).",
    )
    parser.add_argument(
        "--auth-base-url",
        metavar="URL",
        default=None,
        help="Set auth_base_url in .dlt/config.toml for stacks that split auth onto its own host (e.g. local); omit when auth shares the api host (dev/prod).",
    )
    parser.add_argument(
        "--dlthub-client-source",
        metavar="PATH",
        default=None,
        help="Point dlthub-client at a local runtime checkout (editable) for dev/local stacks whose API can outrun the released client; omit for prod (PyPI client).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Stream output from underlying subprocesses (uv, dlthub).",
    )
    parser.add_argument(
        "--no-telemetry",
        action="store_true",
        help="Disable usage telemetry for this run.",
    )
    # Dev/CI only; hidden from --help. Both skip login + playground connection.
    # --setup-only installs deps; --scaffold-only skips deps too.
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--scaffold-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_io_on_windows()
    parser = build_parser()
    args = parser.parse_args(argv)
    telemetry.init(no_telemetry=args.no_telemetry, interactive=stdin_is_interactive())

    try:
        run(args)
    except KeyboardInterrupt:
        telemetry.track_run("cancelled")
        console.print(strings.MSG_CANCELLED)
        return 130
    except WorkspaceDirectoryNotEmptyError as exc:
        telemetry.track_run("failed", error_code=type(exc).__name__)
        print_dir_not_empty(exc.project_dir)
        return 2
    except WorkspaceError as exc:
        telemetry.track_run("failed", error_code=type(exc).__name__)
        print_error(strings.MSG_ERROR_PREFIX, str(exc))
        return 1
    except Exception as exc:
        telemetry.track_run("failed", error_code=type(exc).__name__)
        print_error(strings.MSG_UNEXPECTED_ERROR, str(exc))
        if args.verbose:
            console.print_exception()
        else:
            console.print(strings.MSG_UNEXPECTED_ERROR_HINT)
        return 1
    telemetry.track_run("success")
    return 0


def run(args: argparse.Namespace) -> None:
    interactive = stdin_is_interactive()
    # Banner is decorative — skip it in non-TTY runs where it's just log noise.
    if interactive:
        print_banner()
        console.print()

    telemetry.show_first_run_notice()

    if args.setup_only or args.scaffold_only:
        err_console.print(strings.MSG_TESTING_SHORTCUT_NOTE)

    # The agent picker can't run without a TTY, so a non-interactive run must name the agent.
    if not interactive and args.agent is None and not args.setup_only:
        raise WorkspaceError(strings.ERROR_NO_AGENT_NON_INTERACTIVE)

    verbose = args.verbose
    scaffold = RECOMMENDED.scaffold
    validate_scaffold_name(scaffold)
    if args.agent is not None:
        validate_agent(scaffold=scaffold, agent=args.agent)

    resolution = resolve_workspace_target(args.project_dir)
    project_dir = resolution.project_dir
    if resolution.relocated_from is not None:
        console.print(strings.MSG_RELOCATED.format(relocated_from=resolution.relocated_from, project_dir=project_dir))

    uv_executable = find_uv()
    if uv_executable is None and (
        args.setup_only or confirm(strings.PROMPT_INSTALL_UV, recommended=RECOMMENDED.install_uv)
    ):
        uv_executable = execute_uv_install(verbose=verbose)

    install_deps = uv_executable is not None and not args.scaffold_only
    with substep(
        strings.MSG_CREATING_WORKSPACE,
        strings.MSG_WORKSPACE_READY if install_deps else strings.MSG_WORKSPACE_CREATED,
        verbose=verbose,
    ):
        copy_scaffold(project_dir, scaffold=scaffold, agent=None)
        package_name = apply_workspace_name(project_dir, project_dir.name)
        if args.api_base_url or args.auth_base_url:
            apply_runtime_base_urls(project_dir, api_base_url=args.api_base_url, auth_base_url=args.auth_base_url)
        if args.dlthub_client_source:
            apply_dlthub_client_source(project_dir, args.dlthub_client_source)
        if uv_executable is not None and not args.scaffold_only:
            run_uv_sync(uv_executable, project_dir, verbose=verbose)
    substep_detail(strings.MSG_PACKAGE_NAME.format(package_name=package_name))
    print_created_tree(scaffold)

    if uv_executable is None:
        _finalize_agent(project_dir, scaffold, args, verbose=verbose)
        console.print(strings.MSG_SKIPPED_UV_AND_SYNC)
        print_next_steps(project_dir, scaffold=scaffold, needs_uv_install=True, needs_deps=True)
        return

    if args.scaffold_only:
        _finalize_agent(project_dir, scaffold, args, verbose=verbose)
        console.print(strings.MSG_SKIPPED_SYNC)
        print_next_steps(project_dir, scaffold=scaffold, needs_deps=True)
        return

    if args.setup_only:
        _finalize_agent(project_dir, scaffold, args, verbose=verbose)
        console.print()
        print_next_steps(project_dir, scaffold=scaffold)
        return

    setup_error: str | None = None
    try:
        _login_and_connect_playground(uv_executable, project_dir, verbose=verbose)
    except UvError as exc:
        setup_error = str(exc)
        print_error(strings.MSG_SETUP_FAILED, setup_error)

    agent = _finalize_agent(project_dir, scaffold, args, verbose=verbose)
    skill_path = _entry_skill_path(project_dir, agent)
    plan_skill_path = f"{AGENT_SKILLS_DIR[agent]}/{ONE_SHOT_ENTRY_SKILL}"
    if setup_error is None:
        plan = strings.MSG_LAUNCH_PLAN
        headline = strings.TITLE_ALL_SET
        handoff_prompt = strings.CMD_DEPLOY_RUN_HANDOFF_PROMPT.format(skill_path=skill_path)
        plan_prompt = strings.CMD_DEPLOY_RUN_HANDOFF_PROMPT.format(skill_path=plan_skill_path)
    else:
        plan = strings.MSG_LAUNCH_PLAN_RESOLVE
        headline = strings.TITLE_ALMOST_THERE
        handoff_prompt = strings.CMD_RESOLVE_HANDOFF_PROMPT.format(skill_path=skill_path, error=setup_error)
        plan_prompt = strings.CMD_RESOLVE_HANDOFF_PROMPT.format(
            skill_path=plan_skill_path, error=strings.HINT_ERROR_SHOWN_ABOVE
        )

    if interactive and _agent_launchable(agent):
        print_launch_plan(plan.format(agent=agent), project_dir, plan_prompt)
        launch = confirm(
            strings.PROMPT_LAUNCH_AGENT,
            yes_label=strings.PROMPT_LAUNCH_YES.format(agent=agent),
            no_label=strings.PROMPT_LAUNCH_NO,
        )
        if launch and _launch_agent(project_dir, agent, prompt=handoff_prompt):
            return

    console.print()
    if not interactive:
        print_verbatim(handoff_prompt)
        return
    prompt_copied = copy_to_clipboard(handoff_prompt)
    print_next_steps(
        project_dir,
        scaffold=scaffold,
        agent_prompt=handoff_prompt,
        headline=headline,
        prompt_copied=prompt_copied,
    )


def _finalize_agent(project_dir: Path, scaffold: str, args: argparse.Namespace, *, verbose: bool) -> str:
    """Resolve the agent (prompting unless --agent/--setup-only set it) and lay down its AI files."""
    agent = args.agent or (RECOMMENDED.agent if args.setup_only else choose_agent())
    with substep(
        strings.MSG_ADDING_AGENT_FILES.format(agent=agent),
        strings.MSG_ADDED_AGENT_FILES.format(agent=agent),
        verbose=verbose,
    ):
        overlay_agent(project_dir, scaffold=scaffold, agent=agent)
    return agent


def _entry_skill_path(project_dir: Path, agent: str) -> Path:
    """Absolute path to the bundled entry skill for ``agent`` in the workspace."""
    return project_dir / AGENT_SKILLS_DIR[agent] / ONE_SHOT_ENTRY_SKILL


def _agent_launchable(agent: str) -> bool:
    """True if ``agent`` has a terminal CLI on PATH we can launch."""
    base = AGENT_LAUNCH_COMMANDS.get(agent)
    return base is not None and shutil.which(base[0]) is not None


def _launch_agent(project_dir: Path, agent: str, *, prompt: str) -> bool:
    """Launch ``agent`` in the workspace, seeded with ``prompt``; False if it has no
    terminal CLI on PATH, so the caller falls back to the clipboard panel."""
    base = AGENT_LAUNCH_COMMANDS.get(agent)
    if base is None:
        return False
    executable = shutil.which(base[0])
    if executable is None:
        return False
    console.print(strings.MSG_LAUNCHING_AGENT.format(agent=agent, project_dir=project_dir))
    try:
        subprocess.run([executable, *base[1:], prompt], cwd=project_dir, check=False)
    except OSError:
        return False
    return True


def _login_and_connect_playground(uv_executable: str, project_dir: Path, *, verbose: bool) -> None:
    """Log in and bind the playground workspace, the setup the entry skill assumes is done."""
    with substep(strings.MSG_CONNECTING_DLTHUB, strings.MSG_CONNECTED_DLTHUB, verbose=verbose):
        run_uv_command(uv_executable, project_dir, ["run", "dlthub", "login"], verbose=verbose)
        # The account always has a playground workspace, so connect without --create.
        run_uv_command(
            uv_executable,
            project_dir,
            ["run", "dlthub", "workspace", "connect", PLAYGROUND_WORKSPACE],
            verbose=verbose,
        )


if __name__ == "__main__":
    sys.exit(main())
