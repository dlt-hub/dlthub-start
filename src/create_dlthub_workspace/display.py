"""Rich-powered output: banner, spinners, next-steps panel."""

from __future__ import annotations

import os
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
    "starter_workspace": (
        (strings.STEPS_LABEL_ADD_MOTHERDUCK_CREDENTIALS, None),
        (strings.STEPS_LABEL_RUN_BREWERIES, strings.CMD_DLTHUB_RUN_BREWERIES),
        (strings.STEPS_LABEL_VIEW_JOB_RUNS, strings.CMD_DLTHUB_JOB_RUNS_SHOW_BREWERIES),
    ),
    "minimal_workspace": (
        (strings.STEPS_LABEL_RUN_SAMPLE_SHOP, strings.CMD_DLTHUB_RUN_SAMPLE_SHOP),
        (strings.STEPS_LABEL_VIEW_SAMPLE_SHOP_RUNS, strings.CMD_DLTHUB_JOB_RUNS_SHOW_SAMPLE_SHOP),
        (strings.STEPS_LABEL_EDIT_PIPELINE, None),
    ),
}

CREATED_TREE: dict[str, tuple[str, ...]] = {
    "starter_workspace": (
        "pyproject.toml",
        "starter_pipeline.py",
        "starter_transformations.py",
        "starter_data_quality.py",
        "notebooks/",
        ".dlt/",
        ".agents/",
    ),
    "minimal_workspace": (
        "pyproject.toml",
        "pipeline.py",
        "report_notebook.py",
        "__deployment__.py",
        ".dlt/",
        ".agents/",
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


def print_next_steps(project_dir: Path, *, scaffold: str, agents: tuple[str, ...] = ()) -> None:
    """Post-setup tips panel. Steps are tailored to the chosen scaffold."""
    created_tree = CREATED_TREE[scaffold]
    # Every panel starts the user at "go to the directory" so the rest of the
    # numbered commands can be copy-pasted without context-switching.
    steps: tuple[tuple[str, str | None], ...] = (
        (strings.STEPS_LABEL_CD, strings.CMD_CD.format(project_dir=_cd_target(project_dir))),
        *NEXT_STEPS[scaffold],
    )

    body = Text()
    body.append(f"{strings.LABEL_CREATED}\n\n", style="bold #C6D300")
    for index, entry in enumerate(created_tree):
        branch = "`-- " if index == len(created_tree) - 1 else "|-- "
        body.append(f"  {branch}{entry}\n", style="dim")
    if agents:
        body.append(f"  {strings.LABEL_AI_WORKBENCHES} ", style="dim")
        body.append(", ".join(agents), style="bold #59C1D5")
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
    steps: list[tuple[str, str]] = [
        (strings.STEPS_LABEL_CD, strings.CMD_CD.format(project_dir=_cd_target(project_dir))),
    ]
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

    console.print(
        Panel(
            body,
            title=strings.TITLE_RESUME_PANEL,
            title_align="left",
            border_style="#C6D300",
            padding=(1, 2),
        )
    )
