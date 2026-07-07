"""Interactive prompts shown during the run."""

from __future__ import annotations

import sys
from typing import cast

import beaupy

from . import strings
from .config import AGENTS, COLOR_CYAN, RECOMMENDED
from .display import console

CURSOR = "❯"
CURSOR_STYLE = COLOR_CYAN
TICK_CHAR = "●"
# Re-exported for tests + back-compat. Canonical value lives in strings.py.
RECOMMENDED_SUFFIX = strings.HINT_RECOMMENDED_SUFFIX


def stdin_is_interactive() -> bool:
    """True when both stdin and stdout are TTYs, so arrow-key prompts can run."""
    in_tty = getattr(sys.stdin, "isatty", None)
    out_tty = getattr(sys.stdout, "isatty", None)
    return bool(in_tty and out_tty and in_tty() and out_tty())


def _echo_selection(value: str) -> None:
    """Persist the user's choice after beaupy clears its widget."""
    console.print(f"[{CURSOR_STYLE}]{TICK_CHAR}[/{CURSOR_STYLE}] [bold]{value}[/bold]")


def choose_agent(default: str = RECOMMENDED.agent) -> str:
    """Arrow-key select for the coding agent. Exactly one is chosen."""
    agents = list(AGENTS)
    options = [
        f"[bold]{agent}[/bold]"
        f"{strings.HINT_CODEX_SUFFIX if agent == 'codex' else ''}"
        f"{RECOMMENDED_SUFFIX if agent == RECOMMENDED.agent else ''}"
        for agent in agents
    ]
    default_index = agents.index(default) if default in agents else 0

    console.print(strings.PROMPT_AGENT_HEADER.format(lead=strings.PROMPT_AGENT_LEAD_SETUP))
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


def confirm(
    message: str,
    *,
    default: bool = True,
    recommended: bool | None = None,
    yes_label: str = "Yes",
    no_label: str = "No",
) -> bool:
    """Arrow-key Yes/No confirmation.

    Pass ``recommended=True`` (or ``False``) to badge the recommended choice.
    ``yes_label``/``no_label`` override the option text; the result is still yes=True.
    """
    console.print(f"\n[bold]{message}[/bold]")
    yes = yes_label + (RECOMMENDED_SUFFIX if recommended is True else "")
    no = no_label + (RECOMMENDED_SUFFIX if recommended is False else "")
    choice = cast(
        str,
        beaupy.select(
            [yes, no],
            cursor=CURSOR,
            cursor_style=CURSOR_STYLE,
            cursor_index=0 if default else 1,
        ),
    )
    result = choice == yes
    _echo_selection(yes_label if result else no_label)
    return result
