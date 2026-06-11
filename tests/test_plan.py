"""Tests for build_plan — the decision tree that resolves CLI args + prompts
into a frozen WorkspacePlan.

Mocks every external dependency (find_uv, choose_agent, confirm,
resolve_workspace_target) so each test is fast and deterministic. There is a
single bundled scaffold, so no scaffold prompt is involved.
"""

from __future__ import annotations

import argparse
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from create_dlthub_workspace.config import RECOMMENDED
from create_dlthub_workspace.errors import ScaffoldError
from create_dlthub_workspace.plan import WorkspaceStage, build_plan
from create_dlthub_workspace.scaffold import TargetResolution


def _make_args(**overrides: object) -> argparse.Namespace:
    """Mirror what argparse would produce; tests override individual fields."""
    defaults: dict[str, object] = {
        "project_dir": "/tmp/test_workspace",
        "agent": None,
        "yes": False,
        "verbose": False,
        "skip_uv_sync": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class BuildPlanYesModeTests(unittest.TestCase):
    """`--yes` runs the recommended path with no prompts fired."""

    @patch("create_dlthub_workspace.plan.choose_agent")
    @patch("create_dlthub_workspace.plan.confirm")
    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value="/usr/local/bin/uv")
    def test_uv_present_produces_full_recommended_plan(
        self,
        _find_uv: MagicMock,
        _validate: MagicMock,
        confirm: MagicMock,
        choose_agent: MagicMock,
    ) -> None:
        plan = build_plan(_make_args(yes=True))

        self.assertEqual(plan.stage, WorkspaceStage.FULL)
        self.assertEqual(plan.scaffold, RECOMMENDED.scaffold)
        self.assertEqual(plan.agent, RECOMMENDED.agent)
        self.assertFalse(plan.install_uv)
        self.assertEqual(plan.uv_executable, "/usr/local/bin/uv")
        # --yes never runs the first pipeline (its login is interactive).
        self.assertFalse(plan.run_first_pipeline)
        confirm.assert_not_called()
        choose_agent.assert_not_called()

    @patch("create_dlthub_workspace.plan.confirm")
    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value=None)
    def test_uv_absent_marks_install_uv_without_prompting(
        self,
        _find_uv: MagicMock,
        _validate: MagicMock,
        confirm: MagicMock,
    ) -> None:
        plan = build_plan(_make_args(yes=True))

        self.assertEqual(plan.stage, WorkspaceStage.FULL)
        self.assertTrue(plan.install_uv)
        self.assertIsNone(plan.uv_executable)
        confirm.assert_not_called()

    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value="/usr/local/bin/uv")
    def test_skip_uv_sync_forces_through_uv_install_stage(
        self,
        _find_uv: MagicMock,
        _validate: MagicMock,
    ) -> None:
        plan = build_plan(_make_args(yes=True, skip_uv_sync=True))

        self.assertEqual(plan.stage, WorkspaceStage.THROUGH_UV_INSTALL)
        # The agent is vendored into the scaffold, so the recommended choice is
        # honored even when execution stops before uv sync.
        self.assertEqual(plan.agent, RECOMMENDED.agent)


class BuildPlanInteractiveTests(unittest.TestCase):
    """Interactive mode: uv sync and the first pipeline run happen automatically.

    The only question prompted is install-uv (and only when uv is missing).
    """

    @patch("create_dlthub_workspace.plan.choose_agent", return_value="cursor")
    @patch("create_dlthub_workspace.plan.confirm")
    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value="/usr/local/bin/uv")
    def test_uv_present_runs_full_with_first_pipeline(
        self,
        _find_uv: MagicMock,
        _validate: MagicMock,
        confirm: MagicMock,
        choose_agent: MagicMock,
    ) -> None:
        plan = build_plan(_make_args())

        self.assertEqual(plan.stage, WorkspaceStage.FULL)
        # Single bundled scaffold: always the recommended one, no prompt.
        self.assertEqual(plan.scaffold, RECOMMENDED.scaffold)
        self.assertEqual(plan.agent, "cursor")
        # Sync and the first pipeline run are automatic — no prompts.
        self.assertTrue(plan.run_first_pipeline)
        choose_agent.assert_called_once()
        # uv is already present, so nothing is confirmed at all.
        confirm.assert_not_called()

    @patch("create_dlthub_workspace.plan.choose_agent", return_value="claude")
    @patch("create_dlthub_workspace.plan.confirm", return_value=False)
    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value=None)
    def test_uv_install_declined_stops_at_scaffold_only(
        self,
        _find_uv: MagicMock,
        _validate: MagicMock,
        confirm: MagicMock,
        choose_agent: MagicMock,
    ) -> None:
        plan = build_plan(_make_args())

        self.assertEqual(plan.stage, WorkspaceStage.SCAFFOLD_ONLY)
        self.assertFalse(plan.install_uv)
        self.assertFalse(plan.run_first_pipeline)
        # The agent is asked before the uv prompt, so a SCAFFOLD_ONLY plan still
        # carries the user's actual selection (vendored into the copy).
        self.assertEqual(plan.agent, "claude")
        choose_agent.assert_called_once()
        # Only the uv-install question fires.
        confirm.assert_called_once()

    @patch("create_dlthub_workspace.plan.choose_agent", return_value="claude")
    @patch("create_dlthub_workspace.plan.confirm", return_value=True)
    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value=None)
    def test_uv_install_accepted_runs_full(
        self,
        _find_uv: MagicMock,
        _validate: MagicMock,
        confirm: MagicMock,
        _choose_agent: MagicMock,
    ) -> None:
        plan = build_plan(_make_args())

        self.assertEqual(plan.stage, WorkspaceStage.FULL)
        self.assertTrue(plan.install_uv)
        self.assertTrue(plan.run_first_pipeline)
        # Only the uv-install question fires; sync + first run are automatic.
        confirm.assert_called_once()


class BuildPlanArgOverrideTests(unittest.TestCase):
    """Explicit CLI flags bypass the corresponding prompts."""

    @patch("create_dlthub_workspace.plan.choose_agent")
    @patch("create_dlthub_workspace.plan.confirm", return_value=True)
    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value="/usr/local/bin/uv")
    def test_agent_arg_skips_agent_prompt(
        self,
        _find_uv: MagicMock,
        _validate: MagicMock,
        _confirm: MagicMock,
        choose_agent: MagicMock,
    ) -> None:
        plan = build_plan(_make_args(agent="codex"))

        self.assertEqual(plan.agent, "codex")
        choose_agent.assert_not_called()


class BuildPlanFlagInteractionTests(unittest.TestCase):
    """Documents how flags interact with the prompt path.

    These tests pin down behaviors that have non-obvious side effects (silent
    drops, prompt short-circuits) so any change to flag handling shows up as
    a failing test instead of a silent UX regression.
    """

    @patch("create_dlthub_workspace.plan.choose_agent", return_value="claude")
    @patch("create_dlthub_workspace.plan.confirm")
    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value="/usr/local/bin/uv")
    def test_skip_uv_sync_stops_at_through_uv_install(
        self,
        _find_uv: MagicMock,
        _validate: MagicMock,
        confirm: MagicMock,
        _choose_agent: MagicMock,
    ) -> None:
        # Sync is automatic, but --skip-uv-sync opts out and caps the stage.
        plan = build_plan(_make_args(skip_uv_sync=True))

        self.assertEqual(plan.stage, WorkspaceStage.THROUGH_UV_INSTALL)
        # No sync → no venv → the first-pipeline step doesn't run either.
        self.assertFalse(plan.run_first_pipeline)
        confirm.assert_not_called()

    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value="/usr/local/bin/uv")
    def test_explicit_agent_honored_even_when_stage_skips_uv_sync(
        self,
        _find_uv: MagicMock,
        _validate: MagicMock,
    ) -> None:
        # The vendored agent files don't need uv to be installed, so an explicit
        # --agent selection is preserved even when --skip-uv-sync truncates the
        # stage. Regression guard for the previously-silent input drop.
        plan = build_plan(_make_args(yes=True, agent="claude", skip_uv_sync=True))

        self.assertEqual(plan.stage, WorkspaceStage.THROUGH_UV_INSTALL)
        self.assertEqual(plan.agent, "claude")


class BuildPlanValidationTests(unittest.TestCase):
    """Failures and edge cases."""

    @patch("create_dlthub_workspace.plan.find_uv", return_value="/usr/local/bin/uv")
    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/occupied/playground"), Path("/tmp/occupied")),
    )
    def test_occupied_target_relocates_instead_of_failing(
        self,
        _resolve: MagicMock,
        _find_uv: MagicMock,
    ) -> None:
        # Occupied targets relocate instead of failing; the plan carries both.
        plan = build_plan(_make_args(yes=True))

        self.assertEqual(plan.project_dir, Path("/tmp/occupied/playground"))
        self.assertEqual(plan.relocated_from, Path("/tmp/occupied"))

    @patch("create_dlthub_workspace.plan.choose_agent", return_value="claude")
    @patch("create_dlthub_workspace.plan.confirm", return_value=True)
    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value="/usr/local/bin/uv")
    def test_unknown_agent_arg_raises(
        self,
        _find_uv: MagicMock,
        _validate: MagicMock,
        _confirm: MagicMock,
        _choose_agent: MagicMock,
    ) -> None:
        # validate_agent runs against the scaffold's vendored agents.
        with self.assertRaises(ScaffoldError):
            build_plan(_make_args(agent="does-not-exist"))


class BuildPlanTargetDirTests(unittest.TestCase):
    """build_plan delegates target resolution to resolve_workspace_target and
    threads its result onto the plan. The resolution rules themselves (in-place
    vs playground fallback vs suffixed sibling) are covered in test_scaffold.py.
    """

    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/test_workspace"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value="/usr/local/bin/uv")
    def test_passes_the_raw_arg_to_the_resolver(
        self,
        _find_uv: MagicMock,
        resolve: MagicMock,
    ) -> None:
        # The positional arg flows untouched to the resolver — None when omitted,
        # the string otherwise — which decides in-place vs fallback.
        build_plan(_make_args(project_dir=None, yes=True))
        resolve.assert_called_once_with(None)

        resolve.reset_mock()
        build_plan(_make_args(project_dir="explicit-name", yes=True))
        resolve.assert_called_once_with("explicit-name")

    @patch(
        "create_dlthub_workspace.plan.resolve_workspace_target",
        return_value=TargetResolution(Path("/tmp/explicit-name"), None),
    )
    @patch("create_dlthub_workspace.plan.find_uv", return_value="/usr/local/bin/uv")
    def test_resolved_dir_lands_on_the_plan(
        self,
        _find_uv: MagicMock,
        _resolve: MagicMock,
    ) -> None:
        plan = build_plan(_make_args(project_dir="explicit-name", yes=True))

        self.assertEqual(plan.project_dir, Path("/tmp/explicit-name"))
        self.assertIsNone(plan.relocated_from)


if __name__ == "__main__":
    unittest.main()
