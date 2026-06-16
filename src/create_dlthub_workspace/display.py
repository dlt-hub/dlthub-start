"""Rich-powered output: banner, spinners, next-steps panel."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from . import strings
from .config import VERSION

console = Console()
# Separate stderr stream for out-of-band notes (e.g. the hidden --yes warning),
# so they don't interleave with the primary stdout output.
err_console = Console(stderr=True)

NEXT_STEPS: dict[str, tuple[tuple[str, str | None], ...]] = {
    "managed_destination_workspace": (
        (strings.STEPS_LABEL_RUN_SAMPLE_SHOP, strings.CMD_DLTHUB_RUN_SAMPLE_SHOP),
        (strings.STEPS_LABEL_VIEW_SAMPLE_SHOP_RUNS, strings.CMD_DLTHUB_JOB_RUNS_SHOW_SAMPLE_SHOP),
        (strings.STEPS_LABEL_EDIT_PIPELINE, None),
    ),
}

CREATED_TREE: dict[str, tuple[str, ...]] = {
    "managed_destination_workspace": (
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


@contextmanager
def substep_streaming(running: str, done: str, *, note: str | None = None) -> Iterator[None]:
    """Frame a streamed sub-step, then tick it. No spinner — a live one fights the child for the cursor."""
    console.print(f"[dim]{running}…[/dim]")
    if note:
        console.print(f"[dim]{note}[/dim]")
    console.print()
    try:
        yield
    finally:
        console.print()
    substep_done(done)


STREAM_LOG_STYLE = "dim cyan"


def print_streamed_line(line: str) -> None:
    """Print one streamed-output line verbatim (no markup/highlight), terminal-wrapped."""
    console.print(line, style=STREAM_LOG_STYLE, markup=False, highlight=False, soft_wrap=True)


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


def print_next_steps(
    project_dir: Path,
    *,
    scaffold: str,
    first_pipeline_ran: bool = False,
    prompt_copied: bool = False,
) -> None:
    """Post-setup panel. After the first run, it's just the prompt to hand to the
    agent; otherwise it lists the run/edit steps for the scaffold."""
    body = Text()
    if first_pipeline_ran:
        body.append(f"{strings.STEPS_LABEL_BUILD_OWN_SOURCE}\n\n")
        body.append(f"  {strings.CMD_BUILD_OWN_SOURCE_PROMPT}", style="bold #59C1D5")
        if prompt_copied:
            body.append(f"\n\n  {strings.HINT_PROMPT_COPIED}", style="bold #C6D300")
        body.append(f"\n\n  {strings.LABEL_DOCS} ", style="dim")
        body.append(strings.LINK_DOCS_LABEL, style=f"underline #59C1D5 link {strings.LINK_DOCS_URL}")
    else:
        # Lead with `cd` only for a subdirectory; in the cwd it's noise (`cd .`).
        cd = _cd_target(project_dir)
        cd_step: tuple[tuple[str, str | None], ...] = (
            () if cd == "." else ((strings.STEPS_LABEL_CD, strings.CMD_CD.format(project_dir=cd)),)
        )
        steps: tuple[tuple[str, str | None], ...] = (*cd_step, *NEXT_STEPS[scaffold])
        body.append(f"{strings.LABEL_WHAT_TO_TRY}\n\n", style="bold #C6D300")
        for index, (label, command) in enumerate(steps, start=1):
            body.append(f"  {index}. {label}\n", style="dim")
            if command is not None:
                body.append(f"     {command}\n", style="bold #59C1D5")
            body.append("\n")

    console.print(
        Panel(
            body,
            title=strings.TITLE_NEXT_STEPS_PANEL,
            title_align="left",
            border_style="#C6D300",
            padding=(1, 2),
        )
    )


def print_resume_steps(project_dir: Path, *, uv_installed: bool) -> None:
    """Remaining setup commands. AI workbench files are already in the
    workspace (vendored into the scaffold), so the only thing the user still
    needs to do is finish the uv setup."""
    steps: list[tuple[str, str]] = []
    cd = _cd_target(project_dir)
    if cd != ".":
        steps.append((strings.STEPS_LABEL_CD, strings.CMD_CD.format(project_dir=cd)))
    if not uv_installed:
        steps.append((strings.STEPS_LABEL_INSTALL_UV, strings.CMD_INSTALL_UV_UNIX))
    steps.append((strings.STEPS_LABEL_INSTALL_DEPS, strings.CMD_UV_SYNC))

    body = Text()
    body.append(f"{strings.LABEL_FINISH_SETUP}\n\n", style="bold #C6D300")
    for index, (label, command) in enumerate(steps, start=1):
        body.append(f"  {index}. {label}\n", style="dim")
        body.append(f"     {command}\n\n", style="bold #59C1D5")
    if cd != ".":
        body.append(f"  {strings.MSG_AGENT_WORKSPACE_NOTE}", style="dim")

    console.print(
        Panel(
            body,
            title=strings.TITLE_RESUME_PANEL,
            title_align="left",
            border_style="#C6D300",
            padding=(1, 2),
        )
    )


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
