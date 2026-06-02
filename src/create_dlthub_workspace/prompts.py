"""Interactive prompts. Called only from the planning phase."""

from __future__ import annotations

from typing import cast

import beaupy
from rich.prompt import Prompt

from . import strings
from .config import AGENTS, DEFAULT_PROJECT_NAME, RECOMMENDED, SCAFFOLDS
from .display import console

CURSOR = "❯"
CURSOR_STYLE = "#59C1D5"
TICK_CHAR = "●"
# Re-exported for tests + back-compat. Canonical value lives in strings.py.
RECOMMENDED_SUFFIX = strings.HINT_RECOMMENDED_SUFFIX


def _echo_selection(value: str) -> None:
    """Persist the user's choice after beaupy clears its widget."""
    console.print(f"  [{CURSOR_STYLE}]{TICK_CHAR}[/{CURSOR_STYLE}] [bold]{value}[/bold]")


def choose_project_name(default: str = DEFAULT_PROJECT_NAME) -> str:
    """Free-form text prompt for the workspace name.

    Rich shows the default in dim style at the input position; the user can
    press Enter to accept it or type a different name.
    """
    console.print()  # spacer to match the visual rhythm of the other prompts
    name = Prompt.ask(
        strings.PROMPT_PROJECT_NAME,
        default=default,
        console=console,
        show_default=True,
    ).strip()
    chosen = name or default
    _echo_selection(chosen)
    return chosen


def choose_scaffold(default: str = RECOMMENDED.scaffold) -> str:
    """Arrow-key select for the bundled scaffold."""
    keys = [key for key, _, _ in SCAFFOLDS]
    labels = [label for _, label, _ in SCAFFOLDS]
    options = [
        f"[bold]{label}[/bold]{RECOMMENDED_SUFFIX if key == RECOMMENDED.scaffold else ''}   [dim]{description}[/dim]"
        for key, label, description in SCAFFOLDS
    ]
    default_index = keys.index(default) if default in keys else 0

    console.print(strings.PROMPT_SCAFFOLD_HEADER)
    # beaupy ships no type stubs, so mypy sees the result as Any; cast narrows it
    # to the concrete branch we're using (return_index=True yields an int).
    index = cast(
        int,
        beaupy.select(
            options,
            cursor=CURSOR,
            cursor_style=CURSOR_STYLE,
            cursor_index=default_index,
            return_index=True,
        ),
    )
    _echo_selection(labels[index])
    return keys[index]


def choose_agent(default: str = RECOMMENDED.agent) -> str:
    """Arrow-key select for the coding agent. Exactly one is chosen."""
    agents = list(AGENTS)
    options = [f"[bold]{agent}[/bold]{RECOMMENDED_SUFFIX if agent == RECOMMENDED.agent else ''}" for agent in agents]
    default_index = agents.index(default) if default in agents else 0

    console.print(strings.PROMPT_AGENT_HEADER)
    index = cast(
        int,
        beaupy.select(
            options,
            cursor=CURSOR,
            cursor_style=CURSOR_STYLE,
            cursor_index=default_index,
            return_index=True,
        ),
    )
    _echo_selection(agents[index])
    return agents[index]


def confirm(message: str, *, default: bool = True, recommended: bool | None = None) -> bool:
    """Arrow-key Yes/No confirmation.

    Pass ``recommended=True`` (or ``False``) to badge the recommended choice.
    """
    console.print(f"\n[bold]{message}[/bold]")
    yes_label = "Yes" + (RECOMMENDED_SUFFIX if recommended is True else "")
    no_label = "No" + (RECOMMENDED_SUFFIX if recommended is False else "")
    choice = cast(
        str,
        beaupy.select(
            [yes_label, no_label],
            cursor=CURSOR,
            cursor_style=CURSOR_STYLE,
            cursor_index=0 if default else 1,
        ),
    )
    result = choice == yes_label
    _echo_selection("Yes" if result else "No")
    return result
