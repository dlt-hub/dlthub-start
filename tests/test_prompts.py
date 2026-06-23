"""Tests for the planning-phase prompts (beaupy + rich)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from create_dlthub_workspace import strings
from create_dlthub_workspace.config import AGENTS, RECOMMENDED
from create_dlthub_workspace.display import console
from create_dlthub_workspace.prompts import (
    RECOMMENDED_SUFFIX,
    _echo_selection,
    choose_agent,
    confirm,
)


class EchoSelectionTests(unittest.TestCase):
    def test_prints_value_with_tick_and_bold_markup(self) -> None:
        with console.capture() as cap:
            _echo_selection("claude")
        output = cap.get()

        self.assertIn("claude", output)
        # The tick character is rendered through rich markup; just verify it
        # made it to the output stream.
        self.assertIn("●", output)


class ChooseAgentTests(unittest.TestCase):
    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.beaupy.select", return_value=0)
    def test_returns_selected_agent(
        self,
        _select: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        self.assertEqual(choose_agent(), AGENTS[0])

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.beaupy.select", return_value=0)
    def test_recommended_agent_gets_badge(
        self,
        select: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        choose_agent()
        options = select.call_args.args[0]
        recommended_option = next(opt for opt in options if RECOMMENDED.agent in opt)
        self.assertIn(RECOMMENDED_SUFFIX, recommended_option)

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.beaupy.select", return_value=0)
    def test_defaults_cursor_to_recommended_agent(
        self,
        select: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        choose_agent()
        self.assertEqual(select.call_args.kwargs["cursor_index"], list(AGENTS).index(RECOMMENDED.agent))

    @patch("create_dlthub_workspace.prompts.beaupy.select", return_value=0)
    def test_header_uses_setup_lead(self, _select: MagicMock) -> None:
        with console.capture() as cap:
            choose_agent()
        output = " ".join(cap.get().split())
        self.assertIn(strings.PROMPT_AGENT_LEAD_SETUP, output)


class ConfirmTests(unittest.TestCase):
    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.beaupy.select")
    def test_recommended_true_badges_yes_option(
        self,
        select: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        select.return_value = f"Yes{RECOMMENDED_SUFFIX}"

        result = confirm("Install?", recommended=True)

        self.assertTrue(result)
        options = select.call_args.args[0]
        self.assertEqual(options[0], f"Yes{RECOMMENDED_SUFFIX}")
        self.assertEqual(options[1], "No")

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.beaupy.select", return_value="No")
    def test_no_selection_returns_false(
        self,
        _select: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        self.assertFalse(confirm("Install?"))

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.beaupy.select", return_value="Yes")
    def test_no_recommended_flag_leaves_both_options_unbadged(
        self,
        select: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        confirm("Install?")
        options = select.call_args.args[0]
        self.assertEqual(options, ["Yes", "No"])


if __name__ == "__main__":
    unittest.main()
