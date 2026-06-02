"""Tests for the planning-phase prompts (beaupy + rich)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from create_dlthub_workspace.config import AGENTS, DEFAULT_PROJECT_NAME, RECOMMENDED, SCAFFOLDS
from create_dlthub_workspace.display import console
from create_dlthub_workspace.prompts import (
    RECOMMENDED_SUFFIX,
    _echo_selection,
    choose_agent,
    choose_project_name,
    choose_scaffold,
    confirm,
)


class EchoSelectionTests(unittest.TestCase):
    def test_prints_value_with_tick_and_bold_markup(self) -> None:
        with console.capture() as cap:
            _echo_selection("Starter")
        output = cap.get()

        self.assertIn("Starter", output)
        # The tick character is rendered through rich markup; just verify it
        # made it to the output stream.
        self.assertIn("●", output)


class ChooseScaffoldTests(unittest.TestCase):
    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.beaupy.select", return_value=0)
    def test_returns_selected_scaffold_key(
        self,
        _select: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        self.assertEqual(choose_scaffold(), SCAFFOLDS[0][0])

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.beaupy.select", return_value=0)
    def test_recommended_scaffold_gets_badge(
        self,
        select: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        choose_scaffold()
        options = select.call_args.args[0]
        recommended_label = next(label for key, label, _ in SCAFFOLDS if key == RECOMMENDED.scaffold)
        recommended_option = next(opt for opt in options if recommended_label in opt)
        self.assertIn(RECOMMENDED_SUFFIX, recommended_option)


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


class ChooseProjectNameTests(unittest.TestCase):
    """Directly exercises the rich.Prompt-backed name prompt.

    The build_plan tests only assert that choose_project_name is or isn't
    *called* — they mock its return value. These tests cover the function's
    own contract: default-fallback, whitespace handling, custom default.
    """

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.Prompt.ask", return_value="my-workspace")
    def test_returns_user_input(self, _ask: MagicMock, _console_print: MagicMock) -> None:
        self.assertEqual(choose_project_name(), "my-workspace")

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.Prompt.ask", return_value="")
    def test_empty_input_returns_default(self, _ask: MagicMock, _console_print: MagicMock) -> None:
        self.assertEqual(choose_project_name(), DEFAULT_PROJECT_NAME)

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.Prompt.ask", return_value="   ")
    def test_whitespace_only_input_returns_default(
        self,
        _ask: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        self.assertEqual(choose_project_name(), DEFAULT_PROJECT_NAME)

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.Prompt.ask", return_value="  spaced  ")
    def test_strips_surrounding_whitespace(
        self,
        _ask: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        self.assertEqual(choose_project_name(), "spaced")

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.Prompt.ask", return_value="my-workspace")
    def test_passes_default_to_prompt(
        self,
        ask: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        choose_project_name()
        self.assertEqual(ask.call_args.kwargs["default"], DEFAULT_PROJECT_NAME)

    @patch("create_dlthub_workspace.prompts.console.print")
    @patch("create_dlthub_workspace.prompts.Prompt.ask", return_value="my-workspace")
    def test_custom_default_is_honored(
        self,
        ask: MagicMock,
        _console_print: MagicMock,
    ) -> None:
        choose_project_name(default="custom-default")
        self.assertEqual(ask.call_args.kwargs["default"], "custom-default")


if __name__ == "__main__":
    unittest.main()
