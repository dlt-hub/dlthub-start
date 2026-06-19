"""End-to-end tests: invoke the actual CLI, inspect the resulting workspace.

These tests run real file I/O and (in one case) a real `uv sync`. They're
slow compared to the unit suite. Run via `make test-integration`.

Tests that assert on AI workbench files (`.claude/`, `.cursor/`, `.codex/`,
`AGENTS.md`, etc.) skip gracefully when the scaffolds haven't been populated
yet via `make generate-ai`. Run that first to activate them.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from create_dlthub_workspace.cli import main

from .helpers import EXPECTED_AGENT_ROOT_ENTRIES, scaffold_has_ai_files, silenced


class WorkspaceCreationFastTests(unittest.TestCase):
    """E2E paths that use --scaffold-only: no real `uv sync`, runs in ~1s.

    Validates the orchestration layer (argparse → run → copy_scaffold) end-to-end
    without paying the sync cost.
    """

    def test_scaffold_only_creates_workspace_without_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir) / "test_ws"
            with silenced():
                exit_code = main([str(ws), "--setup-only", "--scaffold-only"])

            self.assertEqual(exit_code, 0)
            self.assertTrue(ws.is_dir())
            self.assertTrue((ws / "pyproject.toml").exists())
            self.assertTrue((ws / "pipeline.py").exists())
            self.assertFalse(
                (ws / ".venv").exists(),
                "--scaffold-only should prevent .venv creation",
            )

    @unittest.skipUnless(
        scaffold_has_ai_files(),
        "AI workbench files not committed yet — run `make generate-ai` first.",
    )
    def test_single_agent_selection_filters_other_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir) / "test_ws"
            with silenced():
                exit_code = main(
                    [str(ws), "--setup-only", "--scaffold-only", "--agent", "claude"],
                )

            self.assertEqual(exit_code, 0)
            for entry in EXPECTED_AGENT_ROOT_ENTRIES["claude"]:
                self.assertTrue(
                    (ws / entry).exists(),
                    f"Selected-agent entry {entry!r} should be present",
                )
            for entry in EXPECTED_AGENT_ROOT_ENTRIES["cursor"]:
                self.assertFalse(
                    (ws / entry).exists(),
                    f"Unselected-agent entry {entry!r} should be filtered out",
                )
            for entry in EXPECTED_AGENT_ROOT_ENTRIES["codex"]:
                self.assertFalse(
                    (ws / entry).exists(),
                    f"Unselected-agent entry {entry!r} should be filtered out",
                )

    @unittest.skipUnless(
        scaffold_has_ai_files(),
        "AI workbench files not committed yet — run `make generate-ai` first.",
    )
    def test_setup_only_brings_in_only_the_recommended_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir) / "test_ws"
            with silenced():
                exit_code = main([str(ws), "--setup-only", "--scaffold-only"])

            self.assertEqual(exit_code, 0)
            # --setup-only uses the recommended agent (claude) and only that agent.
            for entry in EXPECTED_AGENT_ROOT_ENTRIES["claude"]:
                self.assertTrue((ws / entry).exists(), f"recommended agent's {entry!r} should be present")
            for entry in (*EXPECTED_AGENT_ROOT_ENTRIES["cursor"], *EXPECTED_AGENT_ROOT_ENTRIES["codex"]):
                self.assertFalse((ws / entry).exists(), f"non-selected agent's {entry!r} should be absent")


class WorkspaceCreationSlowTests(unittest.TestCase):
    """E2E paths that run a real `uv sync` (~30-60s, network needed)."""

    def test_setup_only_runs_uv_sync_to_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir) / "test_ws"
            with silenced():
                exit_code = main([str(ws), "--setup-only"])

            self.assertEqual(exit_code, 0)
            self.assertTrue((ws / ".venv").is_dir(), "uv sync should have created .venv")
            self.assertTrue((ws / "uv.lock").exists(), "uv sync should have produced a lockfile")


class WorkspaceCollisionTests(unittest.TestCase):
    """End-to-end: a second run at the same path auto-resolves to a free sibling."""

    def test_second_run_at_same_path_relocates_to_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir) / "collision_test"

            with silenced():
                first_exit = main([str(ws), "--setup-only", "--scaffold-only"])
            self.assertEqual(first_exit, 0, "First run should succeed")
            self.assertTrue(ws.is_dir())

            with silenced():
                second_exit = main([str(ws), "--setup-only", "--scaffold-only"])
            self.assertEqual(second_exit, 0, "Second run should succeed by relocating, not fail")

            sibling = ws.with_name("collision_test-1")
            self.assertTrue(sibling.is_dir(), "Second run should land in the -1 sibling")
            self.assertTrue((sibling / "pyproject.toml").exists())
            # The original workspace is left untouched.
            self.assertTrue((ws / "pyproject.toml").exists())


class InstalledEntryPointTests(unittest.TestCase):
    """Spawns the actual CLI binary via subprocess to validate the installed
    entry point (`dlthub-start` on PATH). Uses --scaffold-only to stay fast —
    the sync itself is covered by WorkspaceCreationSlowTests.
    """

    def test_subprocess_invocation_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir) / "test_ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "create_dlthub_workspace",
                    str(ws),
                    "--setup-only",
                    "--scaffold-only",
                ],
                capture_output=True,
                check=False,
            )

            self.assertEqual(
                result.returncode,
                0,
                f"CLI subprocess failed: stderr={result.stderr.decode()!r}",
            )
            self.assertTrue(ws.is_dir())
            self.assertTrue((ws / "pyproject.toml").exists())

    def test_subprocess_relocates_occupied_target(self) -> None:
        # Via `python -m`: an occupied target exits 0, relocates to a sibling, leaves originals.
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir) / "occupied"
            ws.mkdir()
            (ws / "README.md").write_text("not empty\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "create_dlthub_workspace",
                    str(ws),
                    "--setup-only",
                    "--scaffold-only",
                ],
                capture_output=True,
                check=False,
            )

            self.assertEqual(
                result.returncode,
                0,
                f"Expected exit 0 (relocated) for non-empty target; stderr={result.stderr.decode()!r}",
            )
            sibling = ws.with_name("occupied-1")
            self.assertTrue(sibling.is_dir(), "Should have scaffolded into the -1 sibling")
            self.assertTrue((sibling / "pyproject.toml").exists())
            # Original target left as the user had it.
            self.assertEqual((ws / "README.md").read_text(encoding="utf-8"), "not empty\n")


if __name__ == "__main__":
    unittest.main()
