"""Rich-powered output: banner, spinners, next-steps panel."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from rich.console import Console, Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from . import strings
from .config import VERSION

console = Console()
# Separate stderr stream for out-of-band notes (e.g. the hidden testing-shortcut warning),
# so they don't interleave with the primary stdout output.
err_console = Console(stderr=True)

NEXT_STEPS: dict[str, tuple[tuple[str, str | None], ...]] = {
    "minimal_workspace": (
        (strings.STEPS_LABEL_RUN_SAMPLE_SHOP, strings.CMD_DLTHUB_RUN_SAMPLE_SHOP),
        (strings.STEPS_LABEL_VIEW_SAMPLE_SHOP_RUNS, strings.CMD_DLTHUB_JOB_RUNS_SHOW_SAMPLE_SHOP),
        (strings.STEPS_LABEL_EDIT_PIPELINE, None),
    ),
}

CREATED_TREE: dict[str, tuple[str, ...]] = {
    "minimal_workspace": (
        "pyproject.toml",
        "pipeline.py",
        "__deployment__.py",
        ".dlt/",
        "README.md",
    ),
}


def substep_done(message: str) -> None:
    """Tick a finished sub-step with a green check."""
    console.print(f"[green]✓[/green] {message}")


def substep_detail(message: str) -> None:
    """A dimmed detail line beneath a sub-step."""
    console.print(f"[dim]{message}[/dim]")


def print_launch_plan(headline: str, project_dir: Path, prompt: str) -> None:
    """Where the agent will run and the prompt it gets, shown before the launch confirmation."""
    grid = Table.grid(padding=(0, 1))
    grid.add_column(no_wrap=True)
    grid.add_column(overflow="fold")
    grid.add_row(strings.LABEL_WORKSPACE, Text(str(project_dir)))
    grid.add_row(strings.LABEL_PROMPT, Text(prompt))
    console.print(Group(Text(f"\n{headline}", style="bold"), Padding(grid, (0, 0, 0, 2))))


def print_setup_error(message: str) -> None:
    """Red headline + the raw error indented below. Built as Text, not markup,
    so stderr containing bracketed tokens (e.g. `[WARNING]`) renders literally."""
    console.print(
        Group(
            Text(f"\n{strings.MSG_SETUP_FAILED}", style="bold red"),
            Padding(Text(message, style="red"), (0, 0, 0, 2)),
        )
    )


@contextmanager
def substep(running: str, done: str, *, verbose: bool = False) -> Iterator[None]:
    """Spinner while a quick subprocess step runs, swapped for a ✓ line when it finishes."""
    if verbose:
        console.print(f"[dim]{running}…[/dim]")
        yield
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task(running, total=None)
            yield
    substep_done(done)


ROWS = [
    [
        ("", ""),
        ("", ""),
        ("", ""),
        ("", ""),
        ("", ""),
        ("", ""),
        ("", ""),
        ("", ""),
        ("", ""),
        ("", ""),
        ("", ""),
        ("", ""),
    ],
    [
        ("    ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        ("      ", ""),
        ("█", "bold #C6D300"),
    ],
    [
        ("    ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        ("      ", ""),
        ("█", "bold #C6D300"),
    ],
    [
        ("  ", ""),
        ("███", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("██", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        (" ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        (" ", ""),
        ("███", "bold #C6D300"),
    ],
    [
        (" ", ""),
        ("█", "bold #59C1D5"),
        ("  ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        ("  ", ""),
        ("████", "bold #C6D300"),
        (" ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        (" ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
    ],
    [
        (" ", ""),
        ("█", "bold #59C1D5"),
        ("  ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        (" ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        (" ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
    ],
    [
        (" ", ""),
        ("█", "bold #59C1D5"),
        ("  ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        (" ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        (" ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
    ],
    [
        ("  ", ""),
        ("███", "bold #59C1D5"),
        (" ", ""),
        ("█", "bold #59C1D5"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        (" ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("█", "bold #C6D300"),
        ("  ", ""),
        ("███", "bold #C6D300"),
        (" ", ""),
        ("███", "bold #C6D300"),
    ],
]


# Widen each run to offset the ~2:1 tall-to-wide terminal cell ratio.
_LOGO_WIDTH_SCALE = 2


def _build_logo() -> Text:
    logo = Text()
    for row in ROWS:
        for text, style in row:
            logo.append(text * _LOGO_WIDTH_SCALE, style=style)
        logo.append("\n")
    logo.append(f"\n  {strings.HINT_BANNER_TAGLINE}", style="dim")
    return logo


def print_banner() -> None:
    title = Text.from_markup(strings.TITLE_BANNER.format(version=VERSION))
    console.print()
    console.print(
        Panel(
            _build_logo(),
            title=title,
            title_align="left",
            border_style="#59C1D5",
            padding=(1, 2),
        )
    )


def copy_to_clipboard(text: str) -> bool:
    """Best-effort copy ``text`` to the system clipboard. Returns True on success.

    Tries the platform's clipboard tool and silently no-ops (returns False) when
    none is available or the copy fails — it's a convenience, never required.
    """
    if sys.platform == "darwin":
        candidates = [["pbcopy"]]
    elif sys.platform == "win32":
        candidates = [["clip"]]
    else:
        candidates = [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]

    for cmd in candidates:
        if shutil.which(cmd[0]) is None:
            continue
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True, capture_output=True)
            return True
        except (OSError, subprocess.SubprocessError):
            continue
    return False


def _cd_target(project_dir: Path) -> str:
    """Path for the `cd` step. Relative to the cwd the user ran from when the
    workspace sits under it (so the command is short and copy-pasteable);
    absolute otherwise (different parent, or a different Windows drive)."""
    try:
        relative = Path(os.path.relpath(project_dir))
    except ValueError:
        return str(project_dir)
    if os.pardir in relative.parts:
        return str(project_dir)
    return str(relative)


def print_created_tree(scaffold: str) -> None:
    """List the files the scaffold dropped, printed right after creation."""
    entries = CREATED_TREE[scaffold]
    for index, entry in enumerate(entries):
        branch = "`-- " if index == len(entries) - 1 else "|-- "
        console.print(f"[dim]{branch}{entry}[/dim]")


def _print_steps_panel(body: RenderableType, *, title: str) -> None:
    console.print(
        Panel(
            body,
            title=title,
            title_align="left",
            border_style="#C6D300",
            padding=(1, 2),
        )
    )


def print_next_steps(
    project_dir: Path,
    *,
    scaffold: str,
    agent_prompt: str | None = None,
    panel_title: str = strings.TITLE_ALL_SET,
    needs_uv_install: bool = False,
    needs_deps: bool = False,
    prompt_copied: bool = False,
) -> None:
    """The agent hand-off prompt when ``agent_prompt`` is set, else any remaining setup
    commands followed by the steps to run the sample pipeline.

    The hand-off prompt prints without a panel: box borders would be dragged
    into a manual selection when the clipboard copy isn't available."""
    if agent_prompt is not None:
        console.print(Text(f"\n{panel_title}", style="bold #C6D300"))
        console.print(Text(strings.STEPS_LABEL_HANDOFF.format(project_dir=project_dir)))
        console.print()
        console.print(Text(agent_prompt, style="bold #59C1D5"), soft_wrap=True)
        console.print()
        if prompt_copied:
            console.print(Text(strings.HINT_PROMPT_COPIED, style="bold #C6D300"))
        docs = Text(f"{strings.LABEL_DOCS} ", style="dim")
        docs.append(strings.LINK_DOCS_LABEL, style=f"underline #59C1D5 link {strings.LINK_DOCS_URL}")
        console.print(docs)
        return

    body = Text()
    cd = _cd_target(project_dir)
    cd_step: tuple[tuple[str, str | None], ...] = (
        () if cd == "." else ((strings.STEPS_LABEL_CD, strings.CMD_CD.format(project_dir=cd)),)
    )

    sections: list[tuple[str, tuple[tuple[str, str | None], ...]]] = []
    if needs_uv_install or needs_deps:
        finish: list[tuple[str, str | None]] = [*cd_step]
        if needs_uv_install:
            finish.append((strings.STEPS_LABEL_INSTALL_UV, strings.CMD_INSTALL_UV_UNIX))
        if needs_deps:
            finish.append((strings.STEPS_LABEL_INSTALL_DEPS, strings.CMD_UV_SYNC))
        sections.append((strings.LABEL_FINISH_SETUP, tuple(finish)))
        sections.append((strings.LABEL_WHAT_TO_TRY, NEXT_STEPS[scaffold]))
    else:
        sections.append((strings.LABEL_WHAT_TO_TRY, (*cd_step, *NEXT_STEPS[scaffold])))

    step = 1
    for index, (header, steps) in enumerate(sections):
        if index:
            body.append("\n")
        body.append(f"{header}\n\n", style="bold #C6D300")
        for label, command in steps:
            body.append(f"  {step}. {label}\n", style="dim")
            if command is not None:
                body.append(f"     {command}\n", style="bold #59C1D5")
            body.append("\n")
            step += 1

    if cd != ".":
        body.append(f"  {strings.MSG_AGENT_WORKSPACE_NOTE}", style="dim")

    _print_steps_panel(body, title=strings.TITLE_ALMOST_THERE)


def print_dir_not_empty(project_dir: Path) -> None:
    """Render the directory-not-empty response as a clean panel (not a raw error)."""
    body = Text.from_markup(strings.MSG_DIR_NOT_EMPTY.format(project_dir=project_dir))
    console.print(
        Panel(
            body,
            title=strings.TITLE_DIR_NOT_EMPTY,
            title_align="left",
            border_style="#E0A500",
            padding=(1, 2),
        )
    )
