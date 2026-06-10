from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from create_dlthub_workspace.config import AGENTS
from create_dlthub_workspace.errors import ScaffoldError
from create_dlthub_workspace.scaffold import (
    INSTALL_TIME_SENTINEL,
    PER_AGENT_DIR,
    SCAFFOLDS_DIR,
    _stamp_install_time,
    copy_scaffold,
    validate_agent,
    validate_scaffold_name,
    validate_target_dir,
)

# Top-level entries that belong to each agent. Used only by the tests to assert
# the assembled workspace contains the selected agent's files and none other.
AGENT_OWNED = {
    "claude": (".claude", ".claudeignore", ".mcp.json"),
    "cursor": (".cursor", ".cursorignore"),
    "codex": (".codex", ".codexignore", "AGENTS.md", ".agents"),
}


class CopyScaffoldTests(unittest.TestCase):
    def test_copies_bundled_minimal_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "new_workspace"
            copy_scaffold(project_dir, scaffold="minimal_workspace")

            self.assertTrue((project_dir / "pyproject.toml").exists())
            self.assertTrue((project_dir / "pipeline.py").exists())
            self.assertTrue((project_dir / "__deployment__.py").exists())
            self.assertTrue((project_dir / ".dlt" / "config.toml").exists())

    def test_skips_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "new_workspace"
            copy_scaffold(project_dir, scaffold="minimal_workspace")

            # Verify the dev-time artifacts are not propagated to the user's workspace.
            self.assertFalse((project_dir / "__pycache__").exists())
            self.assertFalse((project_dir / ".venv").exists())
            if (project_dir / ".dlt").exists():
                self.assertFalse((project_dir / ".dlt" / "data").exists())
                self.assertFalse((project_dir / ".dlt" / "state").exists())

    def test_no_agent_copies_only_shared_source(self) -> None:
        # Without an agent we lay down just the shared source — no AI files and
        # not the _agents/ pool itself.
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "shared_only"
            copy_scaffold(project_dir, scaffold="minimal_workspace")

            self.assertFalse((project_dir / PER_AGENT_DIR).exists())
            for entries in AGENT_OWNED.values():
                for entry in entries:
                    self.assertFalse((project_dir / entry).exists(), f"{entry} should not be present")

    def test_assembles_only_the_selected_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "claude_only"
            copy_scaffold(project_dir, scaffold="minimal_workspace", agent="claude")

            # The selected agent's files are present...
            for entry in AGENT_OWNED["claude"]:
                self.assertTrue((project_dir / entry).exists(), f"{entry} should be present")
            # ...the others are not, and the _agents/ pool is never shipped.
            for entry in (*AGENT_OWNED["cursor"], *AGENT_OWNED["codex"]):
                self.assertFalse((project_dir / entry).exists(), f"{entry} should not be present")
            self.assertFalse((project_dir / PER_AGENT_DIR).exists())
            # The agent brings its own toolkits manifest, merged into shared .dlt/.
            self.assertTrue((project_dir / ".dlt" / ".toolkits").exists())
            self.assertTrue((project_dir / ".dlt" / "config.toml").exists())

    def test_codex_ships_agents_dir(self) -> None:
        # `.agents/` is codex's skill source and should ship only with codex.
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "codex_only"
            copy_scaffold(project_dir, scaffold="minimal_workspace", agent="codex")

            self.assertTrue((project_dir / ".agents").is_dir())
            self.assertTrue((project_dir / "AGENTS.md").exists())
            self.assertFalse((project_dir / ".claude").exists())
            self.assertFalse((project_dir / ".cursor").exists())

    def test_raises_for_unknown_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ScaffoldError):
                copy_scaffold(Path(tmpdir) / "p", scaffold="does-not-exist")

    def test_raises_for_unknown_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ScaffoldError):
                copy_scaffold(Path(tmpdir) / "p", scaffold="minimal_workspace", agent="bogus")

    def test_raises_when_target_is_not_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "occupied"
            project_dir.mkdir()
            (project_dir / "existing.txt").write_text("hi", encoding="utf-8")

            with self.assertRaises(ScaffoldError):
                copy_scaffold(project_dir, scaffold="minimal_workspace")


class ValidateAgentTests(unittest.TestCase):
    def test_passes_for_every_vendored_agent(self) -> None:
        for agent in AGENTS:
            with self.subTest(agent=agent):
                validate_agent(scaffold="minimal_workspace", agent=agent)  # must not raise

    def test_raises_for_unknown_agent(self) -> None:
        with self.assertRaises(ScaffoldError):
            validate_agent(scaffold="minimal_workspace", agent="does-not-exist")


class PerAgentLayoutTests(unittest.TestCase):
    """Each scaffold must vendor a self-contained tree for every agent."""

    def test_every_agent_is_vendored(self) -> None:
        agents_dir = SCAFFOLDS_DIR / "minimal_workspace" / PER_AGENT_DIR
        for agent in AGENTS:
            with self.subTest(agent=agent):
                self.assertTrue(
                    (agents_dir / agent).is_dir(),
                    f"minimal_workspace/{PER_AGENT_DIR}/{agent} missing — run `make generate-ai`.",
                )


class StampInstallTimeTests(unittest.TestCase):
    def test_replaces_sentinel_with_current_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            manifest = project_dir / ".dlt" / ".toolkits"
            manifest.parent.mkdir()
            manifest.write_text(
                f"init:\n  installed_at: '{INSTALL_TIME_SENTINEL}'\n  agent: claude\n",
                encoding="utf-8",
            )

            _stamp_install_time(project_dir)

            updated = manifest.read_text(encoding="utf-8")
            self.assertNotIn(INSTALL_TIME_SENTINEL, updated)
            # Real timestamps start with a 4-digit year and end with the UTC offset.
            self.assertRegex(updated, r"installed_at: '\d{4}-\d{2}-\d{2}T.+\+00:00'")

    def test_noop_when_manifest_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _stamp_install_time(Path(tmpdir))  # must not raise

    def test_noop_when_sentinel_already_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            manifest = project_dir / ".dlt" / ".toolkits"
            manifest.parent.mkdir()
            already_stamped = "installed_at: '2024-01-01T00:00:00+00:00'\n"
            manifest.write_text(already_stamped, encoding="utf-8")

            _stamp_install_time(project_dir)

            self.assertEqual(manifest.read_text(encoding="utf-8"), already_stamped)


class ValidateTargetDirTests(unittest.TestCase):
    """Direct tests for the target-directory check that gates copy_scaffold."""

    def test_raises_when_dir_exists_and_is_non_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "occupied"
            project_dir.mkdir()
            (project_dir / "existing.txt").write_text("hi", encoding="utf-8")

            with self.assertRaises(ScaffoldError):
                validate_target_dir(project_dir)

    def test_passes_when_dir_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "not_yet_created"
            validate_target_dir(project_dir)  # must not raise

    def test_passes_when_dir_exists_but_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "empty_dir"
            project_dir.mkdir()
            validate_target_dir(project_dir)  # must not raise


class ValidateScaffoldNameTests(unittest.TestCase):
    """Direct tests for scaffold-name validation."""

    def test_raises_for_unknown_scaffold(self) -> None:
        with self.assertRaises(ScaffoldError):
            validate_scaffold_name("does-not-exist")

    def test_passes_for_bundled_scaffolds(self) -> None:
        validate_scaffold_name("minimal_workspace")  # must not raise


class ScaffoldsDirTests(unittest.TestCase):
    def test_bundled_scaffolds_exist(self) -> None:
        self.assertTrue((SCAFFOLDS_DIR / "minimal_workspace").is_dir())


if __name__ == "__main__":
    unittest.main()
