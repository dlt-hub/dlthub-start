"""Tests for the CLI entrypoint: argparse surface + main exit codes."""

from __future__ import annotations

import contextlib
import io
import unittest
from typing import Iterator
from unittest.mock import MagicMock, patch

from pathlib import Path

from create_dlthub_workspace.cli import _workspace_in_list, build_parser, execute_plan, main
from create_dlthub_workspace.config import PLAYGROUND_WORKSPACE
from create_dlthub_workspace.errors import WorkspaceDirectoryNotEmptyError, WorkspaceError
from create_dlthub_workspace.plan import WorkspacePlan, WorkspaceStage


@contextlib.contextmanager
def _silenced() -> Iterator[None]:
    """Suppress stdout + stderr noise from argparse errors and rich.console."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


class BuildParserTests(unittest.TestCase):
    def test_project_dir_is_optional_positional(self) -> None:
        parser = build_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.project_dir)

    def test_rejects_unknown_agent(self) -> None:
        parser = build_parser()
        with _silenced(), self.assertRaises(SystemExit):
            parser.parse_args(["my_workspace", "--agent", "not-an-agent"])

    def test_yes_flag_parses_to_true(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["my_workspace", "--yes"])
        self.assertTrue(args.yes)

    def test_short_yes_flag_parses_to_true(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["my_workspace", "-y"])
        self.assertTrue(args.yes)

    def test_yes_defaults_to_false(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["my_workspace"])
        self.assertFalse(args.yes)

    def test_skip_uv_sync_flag_parses_to_true(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["my_workspace", "--skip-uv-sync"])
        self.assertTrue(args.skip_uv_sync)

    def test_agent_parses_single_value(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["my_workspace", "--agent", "claude"])
        self.assertEqual(args.agent, "claude")

    def test_agent_defaults_to_none(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["my_workspace"])
        self.assertIsNone(args.agent)


class MainExitCodeTests(unittest.TestCase):
    @patch("create_dlthub_workspace.cli.run")
    def test_returns_zero_on_success(self, _run: MagicMock) -> None:
        with _silenced():
            self.assertEqual(main(["my_workspace"]), 0)

    @patch("create_dlthub_workspace.cli.run")
    def test_returns_one_on_workspace_error(self, run: MagicMock) -> None:
        run.side_effect = WorkspaceError("boom")
        with _silenced():
            self.assertEqual(main(["my_workspace"]), 1)

    @patch("create_dlthub_workspace.cli.run")
    def test_returns_130_on_keyboard_interrupt(self, run: MagicMock) -> None:
        run.side_effect = KeyboardInterrupt
        with _silenced():
            self.assertEqual(main(["my_workspace"]), 130)

    @patch("create_dlthub_workspace.cli.print_dir_not_empty")
    @patch("create_dlthub_workspace.cli.run")
    def test_returns_two_and_renders_panel_on_dir_not_empty(
        self, run: MagicMock, print_dir_not_empty: MagicMock
    ) -> None:
        target = Path("/tmp/occupied")
        run.side_effect = WorkspaceDirectoryNotEmptyError(target)
        with _silenced():
            self.assertEqual(main(["my_workspace"]), 2)
        # Routed to the clean response, not the generic error line.
        print_dir_not_empty.assert_called_once_with(target)


def _make_plan(**overrides: object) -> WorkspacePlan:
    """Construct a WorkspacePlan with sensible defaults; tests override fields."""
    defaults: dict[str, object] = {
        "project_dir": Path("/tmp/test_workspace"),
        "relocated_from": None,
        "scaffold": "minimal_workspace",
        "stage": WorkspaceStage.FULL,
        "agent": "claude",
        "uv_executable": "/usr/local/bin/uv",
        "install_uv": False,
        "run_first_pipeline": False,
        "verbose": False,
    }
    defaults.update(overrides)
    return WorkspacePlan(**defaults)  # type: ignore[arg-type]


class ExecutePlanFlowTests(unittest.TestCase):
    """Pins down the orchestration order: copy, then conditional uv work, then next steps."""

    @patch("create_dlthub_workspace.cli.print_next_steps")
    @patch("create_dlthub_workspace.cli.print_resume_steps")
    @patch("create_dlthub_workspace.cli.run_uv_sync")
    @patch("create_dlthub_workspace.cli.execute_uv_install")
    @patch("create_dlthub_workspace.cli.apply_workspace_name", return_value="test-workspace")
    @patch("create_dlthub_workspace.cli.copy_scaffold")
    def test_full_stage_runs_copy_sync_next_steps(
        self,
        copy_scaffold: MagicMock,
        _apply_name: MagicMock,
        execute_uv_install: MagicMock,
        run_uv_sync: MagicMock,
        print_resume_steps: MagicMock,
        print_next_steps: MagicMock,
    ) -> None:
        with _silenced():
            execute_plan(_make_plan(stage=WorkspaceStage.FULL))

        copy_scaffold.assert_called_once()
        run_uv_sync.assert_called_once()
        print_next_steps.assert_called_once()
        execute_uv_install.assert_not_called()  # uv was already present in the plan
        print_resume_steps.assert_not_called()

    @patch("create_dlthub_workspace.cli.console")
    @patch("create_dlthub_workspace.cli.print_next_steps")
    @patch("create_dlthub_workspace.cli.run_uv_sync")
    @patch("create_dlthub_workspace.cli.apply_workspace_name", return_value="test-workspace")
    @patch("create_dlthub_workspace.cli.copy_scaffold")
    def test_relocation_notice_printed_only_when_relocated(
        self,
        _copy_scaffold: MagicMock,
        _apply_name: MagicMock,
        _run_uv_sync: MagicMock,
        _print_next_steps: MagicMock,
        console: MagicMock,
    ) -> None:
        def printed_relocation() -> bool:
            return any("isn't empty" in str(call.args[0]) for call in console.print.call_args_list if call.args)

        execute_plan(_make_plan(stage=WorkspaceStage.FULL, relocated_from=None))
        self.assertFalse(printed_relocation(), "no notice when the requested target was used as-is")

        console.reset_mock()
        execute_plan(
            _make_plan(
                stage=WorkspaceStage.FULL,
                project_dir=Path("/tmp/here/playground"),
                relocated_from=Path("/tmp/here"),
            )
        )
        self.assertTrue(printed_relocation(), "notice fires when we fell back to a different directory")

    @patch("create_dlthub_workspace.cli.run_uv_command")
    @patch("create_dlthub_workspace.cli.print_next_steps")
    @patch("create_dlthub_workspace.cli.run_uv_sync")
    @patch("create_dlthub_workspace.cli.apply_workspace_name", return_value="test-workspace")
    @patch("create_dlthub_workspace.cli.copy_scaffold")
    def test_full_stage_without_first_pipeline_does_not_run_it(
        self,
        _copy_scaffold: MagicMock,
        _apply_name: MagicMock,
        _run_uv_sync: MagicMock,
        _print_next_steps: MagicMock,
        run_uv_command: MagicMock,
    ) -> None:
        with _silenced():
            execute_plan(_make_plan(stage=WorkspaceStage.FULL, run_first_pipeline=False))

        run_uv_command.assert_not_called()

    @patch("create_dlthub_workspace.cli.copy_to_clipboard", return_value=True)
    @patch("create_dlthub_workspace.cli.capture_uv_command", return_value="Name\n----\nMy Workspace\n")
    @patch("create_dlthub_workspace.cli.run_uv_command")
    @patch("create_dlthub_workspace.cli.print_next_steps")
    @patch("create_dlthub_workspace.cli.run_uv_sync")
    @patch("create_dlthub_workspace.cli.apply_workspace_name", return_value="test-workspace")
    @patch("create_dlthub_workspace.cli.copy_scaffold")
    def test_first_pipeline_creates_playground_when_absent_then_runs_and_opens_overview(
        self,
        _copy_scaffold: MagicMock,
        _apply_name: MagicMock,
        _run_uv_sync: MagicMock,
        print_next_steps: MagicMock,
        run_uv_command: MagicMock,
        _capture_uv_command: MagicMock,
        _copy_to_clipboard: MagicMock,
    ) -> None:
        with _silenced():
            execute_plan(_make_plan(stage=WorkspaceStage.FULL, run_first_pipeline=True))

        # Order: log in, connect (--create since absent), run, then open the overview.
        self.assertEqual(run_uv_command.call_count, 4)
        login_args = run_uv_command.call_args_list[0].args[2]
        connect_args = run_uv_command.call_args_list[1].args[2]
        run_args = run_uv_command.call_args_list[2].args[2]
        show_args = run_uv_command.call_args_list[3].args[2]
        self.assertEqual(login_args, ["run", "dlthub", "login"])
        self.assertEqual(connect_args, ["run", "dlthub", "workspace", "connect", PLAYGROUND_WORKSPACE, "--create"])
        self.assertEqual(run_args, ["run", "dlthub", "run", "--follow", "load_sample_shop"])
        self.assertEqual(show_args, ["run", "dlthub", "show"])
        # Only login streams (it's the lone interactive step); the rest run under a spinner.
        self.assertTrue(run_uv_command.call_args_list[0].kwargs["verbose"])
        self.assertFalse(any(call.kwargs["verbose"] for call in run_uv_command.call_args_list[1:]))
        # The panel is told the run already happened, so it shows post-run steps.
        print_next_steps.assert_called_once()
        self.assertTrue(print_next_steps.call_args.kwargs["first_pipeline_ran"])

    @patch("create_dlthub_workspace.cli.copy_to_clipboard", return_value=True)
    @patch(
        "create_dlthub_workspace.cli.capture_uv_command",
        return_value=f"Name        Organization\n----------  ------------\n{PLAYGROUND_WORKSPACE}  Personal\n",
    )
    @patch("create_dlthub_workspace.cli.run_uv_command")
    @patch("create_dlthub_workspace.cli.print_next_steps")
    @patch("create_dlthub_workspace.cli.run_uv_sync")
    @patch("create_dlthub_workspace.cli.apply_workspace_name", return_value="test-workspace")
    @patch("create_dlthub_workspace.cli.copy_scaffold")
    def test_first_pipeline_connects_without_create_when_playground_exists(
        self,
        _copy_scaffold: MagicMock,
        _apply_name: MagicMock,
        _run_uv_sync: MagicMock,
        _print_next_steps: MagicMock,
        run_uv_command: MagicMock,
        _capture_uv_command: MagicMock,
        _copy_to_clipboard: MagicMock,
    ) -> None:
        with _silenced():
            execute_plan(_make_plan(stage=WorkspaceStage.FULL, run_first_pipeline=True))

        # Playground already exists → connect WITHOUT --create (it would error).
        # call_args_list[0] is the login step; connect is next.
        connect_args = run_uv_command.call_args_list[1].args[2]
        self.assertEqual(connect_args, ["run", "dlthub", "workspace", "connect", PLAYGROUND_WORKSPACE])
        self.assertNotIn("--create", connect_args)

    @patch("create_dlthub_workspace.cli.print_next_steps")
    @patch("create_dlthub_workspace.cli.print_resume_steps")
    @patch("create_dlthub_workspace.cli.run_uv_sync")
    @patch("create_dlthub_workspace.cli.execute_uv_install")
    @patch("create_dlthub_workspace.cli.apply_workspace_name", return_value="test-workspace")
    @patch("create_dlthub_workspace.cli.copy_scaffold")
    def test_scaffold_only_stage_stops_after_copy(
        self,
        copy_scaffold: MagicMock,
        _apply_name: MagicMock,
        execute_uv_install: MagicMock,
        run_uv_sync: MagicMock,
        print_resume_steps: MagicMock,
        print_next_steps: MagicMock,
    ) -> None:
        with _silenced():
            execute_plan(
                _make_plan(
                    stage=WorkspaceStage.SCAFFOLD_ONLY,
                    agent="claude",
                    uv_executable=None,
                ),
            )

        copy_scaffold.assert_called_once()
        execute_uv_install.assert_not_called()
        run_uv_sync.assert_not_called()
        print_next_steps.assert_not_called()
        print_resume_steps.assert_called_once_with(Path("/tmp/test_workspace"), uv_installed=False)

    @patch("create_dlthub_workspace.cli.print_next_steps")
    @patch("create_dlthub_workspace.cli.print_resume_steps")
    @patch("create_dlthub_workspace.cli.run_uv_sync")
    @patch("create_dlthub_workspace.cli.execute_uv_install", return_value="/usr/local/bin/uv")
    @patch("create_dlthub_workspace.cli.apply_workspace_name", return_value="test-workspace")
    @patch("create_dlthub_workspace.cli.copy_scaffold")
    def test_through_uv_install_stage_installs_uv_then_stops(
        self,
        copy_scaffold: MagicMock,
        _apply_name: MagicMock,
        execute_uv_install: MagicMock,
        run_uv_sync: MagicMock,
        print_resume_steps: MagicMock,
        print_next_steps: MagicMock,
    ) -> None:
        with _silenced():
            execute_plan(
                _make_plan(
                    stage=WorkspaceStage.THROUGH_UV_INSTALL,
                    agent="claude",
                    uv_executable=None,
                    install_uv=True,
                ),
            )

        copy_scaffold.assert_called_once()
        execute_uv_install.assert_called_once()
        run_uv_sync.assert_not_called()
        print_next_steps.assert_not_called()
        print_resume_steps.assert_called_once_with(Path("/tmp/test_workspace"), uv_installed=True)


class WorkspaceInListTests(unittest.TestCase):
    """Parsing of `dlthub workspace list` output (space-padded table, Name first)."""

    # Mirrors the real CLI output: header, separator, then space-padded rows.
    SAMPLE = (
        "Name                 Organization         ID                                    Role\n"
        "-------------------  -------------------  ------------------------------------  ------\n"
        "My Workspace         Personal Workspaces  927a586a-9d98-40ae-a70d-46b02ee19d80  owner\n"
        "playground           Personal Workspaces  ebe84413-790a-41c1-9947-37ce70a491d9  owner\n"
    )

    def test_detects_existing_workspace(self) -> None:
        self.assertTrue(_workspace_in_list(self.SAMPLE, "playground"))

    def test_absent_workspace_returns_false(self) -> None:
        self.assertFalse(_workspace_in_list(self.SAMPLE, "Sandbox"))

    def test_matches_name_with_internal_spaces(self) -> None:
        # "My Workspace" has a single internal space; columns split on 2+ spaces.
        self.assertTrue(_workspace_in_list(self.SAMPLE, "My Workspace"))

    def test_header_and_separator_rows_are_ignored(self) -> None:
        self.assertFalse(_workspace_in_list(self.SAMPLE, "Name"))

    def test_empty_output_returns_false(self) -> None:
        self.assertFalse(_workspace_in_list("", "Playground"))


if __name__ == "__main__":
    unittest.main()
