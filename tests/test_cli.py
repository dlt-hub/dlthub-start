"""Tests for the CLI entrypoint: argparse surface + the linear run() orchestration."""

from __future__ import annotations

import argparse
import contextlib
import io
import unittest
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, patch

from create_dlthub_workspace import strings
from create_dlthub_workspace.cli import _entry_skill_path, _launch_agent, _workspace_in_list, build_parser, main, run
from create_dlthub_workspace.config import PLAYGROUND_WORKSPACE, RECOMMENDED
from create_dlthub_workspace.errors import UvError, WorkspaceDirectoryNotEmptyError, WorkspaceError
from create_dlthub_workspace.scaffold import TargetResolution

_HANDOFF_PROMPT = strings.CMD_DEPLOY_RUN_HANDOFF_PROMPT.format(
    skill_path=_entry_skill_path(Path("/tmp/test_workspace"), "claude")
)
_SETUP_ERROR = "dlthub login blew up"
_RESOLVE_PROMPT = strings.CMD_RESOLVE_HANDOFF_PROMPT.format(
    skill_path=_entry_skill_path(Path("/tmp/test_workspace"), "claude"),
    error=_SETUP_ERROR,
)


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

    def test_setup_only_flag_parses_to_true(self) -> None:
        # --setup-only stays functional for tests/CI even though it's hidden from --help.
        parser = build_parser()
        args = parser.parse_args(["my_workspace", "--setup-only"])
        self.assertTrue(args.setup_only)

    def test_setup_only_defaults_to_false(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["my_workspace"])
        self.assertFalse(args.setup_only)

    def test_testing_shortcuts_are_hidden_from_help(self) -> None:
        help_text = build_parser().format_help()
        self.assertNotIn("--setup-only", help_text)
        self.assertNotIn("--scaffold-only", help_text)

    def test_scaffold_only_flag_parses_to_true(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["my_workspace", "--scaffold-only"])
        self.assertTrue(args.scaffold_only)

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
        print_dir_not_empty.assert_called_once_with(target)

    @patch("create_dlthub_workspace.cli.run")
    def test_unexpected_exception_is_caught_not_raised(self, run: MagicMock) -> None:
        run.side_effect = RuntimeError("kaboom")
        with _silenced():
            self.assertEqual(main(["my_workspace"]), 1)


def _make_args(**overrides: object) -> argparse.Namespace:
    """Mirror what argparse produces; tests override individual fields."""
    defaults: dict[str, object] = {
        "project_dir": "/tmp/test_workspace",
        "agent": None,
        "api_base_url": None,
        "auth_base_url": None,
        "dlthub_client_source": None,
        "setup_only": False,
        "verbose": False,
        "scaffold_only": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# Every side-effecting step run() calls, patched so tests exercise only control flow.
_STEP_TARGETS = (
    "copy_scaffold",
    "overlay_agent",
    "apply_workspace_name",
    "resolve_workspace_target",
    "find_uv",
    "confirm",
    "choose_agent",
    "stdin_is_interactive",
    "execute_uv_install",
    "run_uv_sync",
    "run_uv_command",
    "capture_uv_command",
    "copy_to_clipboard",
    "_agent_launchable",
    "_launch_agent",
    "print_banner",
    "print_created_tree",
    "print_next_steps",
)


class RunFlowTests(unittest.TestCase):
    """run() orchestration: uv → scaffold + deps → login/connect → agent files → hand-off."""

    def setUp(self) -> None:
        self.m: dict[str, MagicMock] = {}
        for name in _STEP_TARGETS:
            patcher = patch(f"create_dlthub_workspace.cli.{name}")
            self.m[name] = patcher.start()
            self.addCleanup(patcher.stop)
        self.m["apply_workspace_name"].return_value = "test-workspace"
        self.m["find_uv"].return_value = "/usr/local/bin/uv"
        self.m["confirm"].return_value = True
        self.m["choose_agent"].return_value = "claude"
        self.m["stdin_is_interactive"].return_value = True
        self.m["execute_uv_install"].return_value = "/usr/local/bin/uv"
        self.m["copy_to_clipboard"].return_value = True
        self.m["_agent_launchable"].return_value = True
        self.m["_launch_agent"].return_value = False
        self.m["capture_uv_command"].return_value = "Name\n----\n"
        self.m["resolve_workspace_target"].return_value = TargetResolution(Path("/tmp/test_workspace"), None)

    def _run(self, **overrides: object) -> None:
        with _silenced():
            run(_make_args(**overrides))

    def test_agent_files_added_then_handoff_prompt_shown(self) -> None:
        order = MagicMock()
        order.attach_mock(self.m["copy_scaffold"], "copy_scaffold")
        order.attach_mock(self.m["run_uv_command"], "run_uv_command")
        order.attach_mock(self.m["overlay_agent"], "overlay_agent")

        self._run()

        names = [c[0] for c in order.mock_calls]
        self.assertLess(names.index("copy_scaffold"), names.index("run_uv_command"))
        self.assertLess(names.index("run_uv_command"), names.index("overlay_agent"))
        # Shared scaffold carries no agent; the overlay supplies it last.
        self.assertIsNone(self.m["copy_scaffold"].call_args.kwargs["agent"])
        self.m["overlay_agent"].assert_called_once()
        self.m["choose_agent"].assert_called_once()
        self.m["print_next_steps"].assert_called_once()
        self.assertEqual(
            self.m["print_next_steps"].call_args.kwargs["agent_prompt"],
            _HANDOFF_PROMPT,
        )

    def test_launched_agent_replaces_the_next_steps_panel(self) -> None:
        self.m["_launch_agent"].return_value = True

        self._run()

        self.m["_launch_agent"].assert_called_once_with(Path("/tmp/test_workspace"), "claude", prompt=_HANDOFF_PROMPT)
        # A successful launch is the hand-off; the manual fallback is skipped.
        self.m["copy_to_clipboard"].assert_not_called()
        self.m["print_next_steps"].assert_not_called()

    def test_declining_launch_copies_and_prints_the_handoff_prompt(self) -> None:
        self.m["confirm"].return_value = False

        self._run()

        self.m["_launch_agent"].assert_not_called()
        self.m["copy_to_clipboard"].assert_called_once_with(_HANDOFF_PROMPT)
        kwargs = self.m["print_next_steps"].call_args.kwargs
        self.assertEqual(kwargs["agent_prompt"], _HANDOFF_PROMPT)
        self.assertEqual(kwargs["panel_title"], strings.TITLE_ALL_SET)

    def test_unlaunchable_agent_skips_the_prompt_and_prints_the_handoff(self) -> None:
        self.m["_agent_launchable"].return_value = False

        self._run()

        self.m["confirm"].assert_not_called()
        self.m["_launch_agent"].assert_not_called()
        self.assertEqual(
            self.m["print_next_steps"].call_args.kwargs["agent_prompt"],
            _HANDOFF_PROMPT,
        )

    def test_login_failure_still_hands_off_with_resolve_prompt(self) -> None:
        self.m["run_uv_command"].side_effect = UvError(_SETUP_ERROR)

        self._run()

        self.m["overlay_agent"].assert_called_once()
        self.assertEqual(self.m["_launch_agent"].call_args.kwargs["prompt"], _RESOLVE_PROMPT)
        kwargs = self.m["print_next_steps"].call_args.kwargs
        self.assertEqual(kwargs["agent_prompt"], _RESOLVE_PROMPT)
        self.assertEqual(kwargs["panel_title"], strings.TITLE_ALMOST_THERE)

    def test_non_interactive_login_failure_prints_resolve_prompt(self) -> None:
        self.m["stdin_is_interactive"].return_value = False
        self.m["run_uv_command"].side_effect = UvError(_SETUP_ERROR)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run(_make_args(agent="claude"))
        out = buf.getvalue()

        self.m["_launch_agent"].assert_not_called()
        self.m["print_next_steps"].assert_not_called()
        self.m["copy_to_clipboard"].assert_not_called()
        self.assertIn("Diagnose", out)
        self.assertIn(_SETUP_ERROR, out)

    def test_explicit_agent_skips_the_prompt(self) -> None:
        self._run(agent="codex")
        self.m["choose_agent"].assert_not_called()
        self.assertEqual(self.m["overlay_agent"].call_args.kwargs["agent"], "codex")

    def test_non_interactive_without_agent_fails_fast(self) -> None:
        self.m["stdin_is_interactive"].return_value = False
        with self.assertRaises(WorkspaceError):
            self._run()
        self.m["copy_scaffold"].assert_not_called()

    def test_non_interactive_with_explicit_agent_proceeds(self) -> None:
        self.m["stdin_is_interactive"].return_value = False
        self._run(agent="claude")
        self.m["choose_agent"].assert_not_called()
        self.m["overlay_agent"].assert_called_once()
        self.m["_launch_agent"].assert_not_called()
        self.m["copy_to_clipboard"].assert_not_called()
        self.m["print_next_steps"].assert_not_called()

    def test_non_interactive_setup_only_defaults_without_failing(self) -> None:
        self.m["stdin_is_interactive"].return_value = False
        self._run(setup_only=True)
        self.assertEqual(self.m["overlay_agent"].call_args.kwargs["agent"], RECOMMENDED.agent)

    def test_setup_only_skips_handoff_but_adds_agent_files(self) -> None:
        self._run(setup_only=True)
        self.m["run_uv_command"].assert_not_called()
        self.m["choose_agent"].assert_not_called()
        self.assertEqual(self.m["overlay_agent"].call_args.kwargs["agent"], RECOMMENDED.agent)
        self.assertIsNone(self.m["print_next_steps"].call_args.kwargs.get("agent_prompt"))

    def test_uv_declined_stops_at_scaffold_only_but_adds_agent_files(self) -> None:
        self.m["find_uv"].return_value = None
        self.m["confirm"].return_value = False

        self._run()

        self.m["execute_uv_install"].assert_not_called()
        self.m["run_uv_sync"].assert_not_called()
        self.m["overlay_agent"].assert_called_once()
        self.m["print_next_steps"].assert_called_once()
        kwargs = self.m["print_next_steps"].call_args.kwargs
        self.assertIsNone(kwargs.get("agent_prompt"))
        self.assertTrue(kwargs["needs_uv_install"])
        self.assertTrue(kwargs["needs_deps"])

    def test_scaffold_only_stops_after_install_but_adds_agent_files(self) -> None:
        self._run(scaffold_only=True)
        self.m["run_uv_sync"].assert_not_called()
        self.m["overlay_agent"].assert_called_once()
        self.m["print_next_steps"].assert_called_once()
        kwargs = self.m["print_next_steps"].call_args.kwargs
        self.assertIsNone(kwargs.get("agent_prompt"))
        self.assertTrue(kwargs["needs_deps"])
        self.assertFalse(kwargs.get("needs_uv_install", False))

    def test_login_connect_creates_playground_when_absent(self) -> None:
        self.m["capture_uv_command"].return_value = "Name\n----\nMy Workspace\n"

        self._run()

        run_uv_command = self.m["run_uv_command"]
        self.assertEqual(run_uv_command.call_count, 2)
        login_args = run_uv_command.call_args_list[0].args[2]
        connect_args = run_uv_command.call_args_list[1].args[2]
        self.assertEqual(login_args, ["run", "dlthub", "login"])
        self.assertEqual(connect_args, ["run", "dlthub", "workspace", "connect", PLAYGROUND_WORKSPACE, "--create"])
        # Login and connect run quietly (output surfaces only on error); nothing streams.
        self.assertFalse(any(c.kwargs["verbose"] for c in run_uv_command.call_args_list))
        self.assertFalse(any(c.kwargs.get("stream", False) for c in run_uv_command.call_args_list))

    def test_login_connect_skips_create_when_playground_exists(self) -> None:
        self.m[
            "capture_uv_command"
        ].return_value = f"Name        Organization\n----------  ------------\n{PLAYGROUND_WORKSPACE}  Personal\n"

        self._run()

        connect_args = self.m["run_uv_command"].call_args_list[1].args[2]
        self.assertEqual(connect_args, ["run", "dlthub", "workspace", "connect", PLAYGROUND_WORKSPACE])

    @patch("create_dlthub_workspace.cli.console")
    def test_relocation_notice_printed_only_when_relocated(self, console: MagicMock) -> None:
        def printed_relocation() -> bool:
            return any("isn't empty" in str(c.args[0]) for c in console.print.call_args_list if c.args)

        self._run()
        self.assertFalse(printed_relocation())

        console.reset_mock()
        self.m["resolve_workspace_target"].return_value = TargetResolution(
            Path("/tmp/here/playground"), Path("/tmp/here")
        )
        self._run()
        self.assertTrue(printed_relocation())


class RunNoticeTests(unittest.TestCase):
    """run() warns (on stderr) when a hidden testing shortcut is used."""

    def _run_with(self, **flags: bool) -> MagicMock:
        with (
            patch("create_dlthub_workspace.cli.print_banner"),
            patch("create_dlthub_workspace.cli.stdin_is_interactive", return_value=True),
            patch("create_dlthub_workspace.cli.resolve_workspace_target") as resolve,
            patch("create_dlthub_workspace.cli.validate_scaffold_name"),
            patch("create_dlthub_workspace.cli.copy_scaffold"),
            patch("create_dlthub_workspace.cli.overlay_agent"),
            patch("create_dlthub_workspace.cli.apply_workspace_name", return_value="ws"),
            patch("create_dlthub_workspace.cli.find_uv", return_value="/usr/local/bin/uv"),
            patch("create_dlthub_workspace.cli.run_uv_sync"),
            patch("create_dlthub_workspace.cli.run_uv_command"),
            patch("create_dlthub_workspace.cli.capture_uv_command", return_value="Name\n----\n"),
            patch("create_dlthub_workspace.cli.copy_to_clipboard", return_value=False),
            patch("create_dlthub_workspace.cli.print_created_tree"),
            patch("create_dlthub_workspace.cli.confirm", return_value=False),
            patch("create_dlthub_workspace.cli._launch_agent", return_value=False),
            patch("create_dlthub_workspace.cli.choose_agent", return_value="claude"),
            patch("create_dlthub_workspace.cli.print_next_steps"),
            patch("create_dlthub_workspace.cli.err_console") as err_console,
            _silenced(),
        ):
            resolve.return_value = TargetResolution(Path("/tmp/test_workspace"), None)
            run(_make_args(**flags))
        return err_console

    def test_setup_only_prints_testing_notice(self) -> None:
        self._run_with(setup_only=True).print.assert_called_once()

    def test_scaffold_only_prints_testing_notice(self) -> None:
        self._run_with(scaffold_only=True).print.assert_called_once()

    def test_both_shortcuts_print_a_single_notice(self) -> None:
        self._run_with(setup_only=True, scaffold_only=True).print.assert_called_once()

    def test_interactive_run_prints_no_notice(self) -> None:
        self._run_with().print.assert_not_called()


class LaunchAgentTests(unittest.TestCase):
    """_launch_agent: runs a detected CLI in the workspace, else reports False."""

    @patch("create_dlthub_workspace.cli.subprocess.run")
    @patch("create_dlthub_workspace.cli.shutil.which", return_value="/usr/local/bin/claude")
    def test_runs_detected_cli_seeded_with_prompt(self, _which: MagicMock, run_cmd: MagicMock) -> None:
        with _silenced():
            launched = _launch_agent(Path("/tmp/ws"), "claude", prompt="do the thing")

        self.assertTrue(launched)
        run_cmd.assert_called_once_with(["/usr/local/bin/claude", "do the thing"], cwd=Path("/tmp/ws"), check=False)

    @patch("create_dlthub_workspace.cli.subprocess.run")
    @patch("create_dlthub_workspace.cli.shutil.which", return_value=None)
    def test_returns_false_when_cli_not_on_path(self, _which: MagicMock, run_cmd: MagicMock) -> None:
        self.assertFalse(_launch_agent(Path("/tmp/ws"), "claude", prompt="x"))
        run_cmd.assert_not_called()

    @patch("create_dlthub_workspace.cli.shutil.which")
    def test_returns_false_for_agent_without_launch_command(self, which: MagicMock) -> None:
        self.assertFalse(_launch_agent(Path("/tmp/ws"), "cursor", prompt="x"))
        which.assert_not_called()

    @patch("create_dlthub_workspace.cli.subprocess.run", side_effect=OSError("exec failed"))
    @patch("create_dlthub_workspace.cli.shutil.which", return_value="/usr/local/bin/claude")
    def test_returns_false_when_spawn_fails(self, _which: MagicMock, _run: MagicMock) -> None:
        with _silenced():
            self.assertFalse(_launch_agent(Path("/tmp/ws"), "claude", prompt="x"))


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
