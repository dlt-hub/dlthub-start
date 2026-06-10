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


@contextmanager
def step(description: str, *, verbose: bool = False) -> Iterator[None]:
    """Show a spinner during a subprocess step, or a plain header in verbose mode."""
    if verbose:
        console.print(f"[bold]{description}[/bold]")
        yield
        return
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task(description, total=None)
        yield


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


def _build_logo() -> Text:
    logo = Text()
    for row in ROWS:
        for text, style in row:
            logo.append(text, style=style)
        logo.append("\n")
    logo.append(f"\n  {strings.HINT_BANNER_TAGLINE}", style="dim")
    return logo


def print_banner() -> None:
    title = Text.from_markup(strings.TITLE_BANNER.format(version=VERSION))
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


def print_next_steps(
    project_dir: Path,
    *,
    scaffold: str,
    agent: str | None = None,
    first_pipeline_ran: bool = False,
    prompt_copied: bool = False,
) -> None:
    """Post-setup tips panel. Steps are tailored to the chosen scaffold.

    When ``first_pipeline_ran`` is True, the run / view-runs steps already
    happened during setup, so the panel shows the post-run step instead.
    ``prompt_copied`` flips the wording to say the prompt is already on the
    clipboard (the actual copy happens in the orchestration layer).
    """
    created_tree = CREATED_TREE[scaffold]
    # Lead with "go to the directory" only when the workspace is a subdirectory;
    # when it's the current directory (cwd) the cd step is noise (`cd .`).
    cd = _cd_target(project_dir)
    cd_step: tuple[tuple[str, str | None], ...] = (
        () if cd == "." else ((strings.STEPS_LABEL_CD, strings.CMD_CD.format(project_dir=cd)),)
    )
    if first_pipeline_ran:
        # The run / view-runs steps already happened during setup. Point the user
        # at building their own pipeline, with a verbatim prompt to paste into the
        # coding agent they chose (the prompt itself is never reformatted).
        label_template = (
            strings.STEPS_LABEL_BUILD_OWN_SOURCE_COPIED if prompt_copied else strings.STEPS_LABEL_BUILD_OWN_SOURCE
        )
        label = label_template.format(agent=agent or "coding")
        next_steps: tuple[tuple[str, str | None], ...] = ((label, strings.CMD_BUILD_OWN_SOURCE_PROMPT),)
    else:
        next_steps = NEXT_STEPS[scaffold]
    steps: tuple[tuple[str, str | None], ...] = (*cd_step, *next_steps)

    body = Text()
    body.append(f"{strings.LABEL_CREATED}\n\n", style="bold #C6D300")
    for index, entry in enumerate(created_tree):
        branch = "`-- " if index == len(created_tree) - 1 else "|-- "
        body.append(f"  {branch}{entry}\n", style="dim")
    if agent:
        body.append(f"  {strings.LABEL_CODING_AGENT} ", style="dim")
        body.append(agent, style="bold #59C1D5")
        body.append("\n")
    body.append("\n")
    body.append(f"{strings.LABEL_WHAT_TO_TRY}\n\n", style="bold #C6D300")
    for index, (label, command) in enumerate(steps, start=1):
        body.append(f"  {index}. {label}\n", style="dim")
        if command is not None:
            body.append(f"     {command}\n", style="bold #59C1D5")
        body.append("\n")
    body.append(f"  {strings.LABEL_DOCS} ", style="dim")
    body.append(
        strings.LINK_DOCS_LABEL,
        style=f"underline #59C1D5 link {strings.LINK_DOCS_URL}",
    )
    if cd != ".":
        body.append(f"\n\n  {strings.MSG_AGENT_WORKSPACE_NOTE}", style="dim")

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
    body.append(f"  {strings.LABEL_DOCS} ", style="dim")
    body.append(
        strings.LINK_DOCS_LABEL,
        style=f"underline #59C1D5 link {strings.LINK_DOCS_URL}",
    )
    if cd != ".":
        body.append(f"\n\n  {strings.MSG_AGENT_WORKSPACE_NOTE}", style="dim")

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
