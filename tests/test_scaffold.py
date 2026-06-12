from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

from create_dlthub_workspace.config import AGENTS, PLAYGROUND_WORKSPACE
from create_dlthub_workspace.errors import ScaffoldError
from create_dlthub_workspace.scaffold import (
    BENIGN_ENTRIES,
    INSTALL_TIME_SENTINEL,
    PER_AGENT_DIR,
    SCAFFOLDS_DIR,
    _stamp_install_time,
    copy_scaffold,
    first_available_dir,
    overlay_agent,
    resolve_workspace_target,
    validate_agent,
    validate_scaffold_name,
    validate_target_dir,
)


@contextmanager
def _chdir(target: Path) -> Iterator[None]:
    """Run the body with ``target`` as the current working directory."""
    previous = os.getcwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(previous)


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


class OverlayAgentTests(unittest.TestCase):
    def test_overlays_agent_onto_shared_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "ws"
            copy_scaffold(project_dir, scaffold="minimal_workspace", agent=None)
            for entry in AGENT_OWNED["claude"]:
                self.assertFalse((project_dir / entry).exists())

            overlay_agent(project_dir, scaffold="minimal_workspace", agent="claude")

            for entry in AGENT_OWNED["claude"]:
                self.assertTrue((project_dir / entry).exists(), f"{entry} should be present")
            manifest = project_dir / ".dlt" / ".toolkits"
            self.assertNotIn(INSTALL_TIME_SENTINEL, manifest.read_text(encoding="utf-8"))

    def test_raises_for_unknown_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "ws"
            copy_scaffold(project_dir, scaffold="minimal_workspace", agent=None)
            with self.assertRaises(ScaffoldError):
                overlay_agent(project_dir, scaffold="minimal_workspace", agent="bogus")


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

    def test_raises_when_a_file_sits_on_the_path(self) -> None:
        # A plain file on the target name counts as occupied — and must not crash
        # the way `any(path.iterdir())` would on a non-directory.
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "afile"
            target.write_text("hi", encoding="utf-8")

            with self.assertRaises(ScaffoldError):
                validate_target_dir(target)

    def test_passes_when_dir_holds_only_benign_entries(self) -> None:
        # An IDE/VCS-cluttered-but-otherwise-empty dir (e.g. `git init` + PyCharm)
        # still initializes in place rather than counting as occupied.
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "looks_empty"
            project_dir.mkdir()
            (project_dir / ".git").mkdir()
            (project_dir / ".idea").mkdir()
            (project_dir / ".DS_Store").write_text("", encoding="utf-8")

            validate_target_dir(project_dir)  # must not raise

    def test_raises_when_benign_entries_mixed_with_real_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "has_real_file"
            project_dir.mkdir()
            (project_dir / ".git").mkdir()
            (project_dir / "main.py").write_text("print('hi')\n", encoding="utf-8")

            with self.assertRaises(ScaffoldError):
                validate_target_dir(project_dir)

    def test_raises_scaffold_error_when_target_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "locked"
            project_dir.mkdir()
            with patch.object(Path, "iterdir", side_effect=PermissionError("denied")):
                with self.assertRaises(ScaffoldError):
                    validate_target_dir(project_dir)


class BenignEntriesInvariantTests(unittest.TestCase):
    """The allowlist must never name something the scaffold itself writes."""

    def test_benign_entries_disjoint_from_scaffold_top_level(self) -> None:
        # A benign name that the scaffold also ships would clobber it on in-place init.
        scaffold = SCAFFOLDS_DIR / "minimal_workspace"
        written_top_level = {p.name for p in scaffold.iterdir() if p.name != PER_AGENT_DIR}
        agents_dir = scaffold / PER_AGENT_DIR
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir():
                written_top_level.update(p.name for p in agent_dir.iterdir())

        collisions = BENIGN_ENTRIES & written_top_level
        self.assertEqual(
            collisions,
            set(),
            f"BENIGN_ENTRIES names scaffold-shipped entries {collisions} — they'd be clobbered on in-place init",
        )


class FirstAvailableDirTests(unittest.TestCase):
    """The ``base`` → ``base-1`` → ``base-2`` … suffix search."""

    def test_returns_base_when_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "ws"
            self.assertEqual(first_available_dir(base), base)

    def test_returns_base_when_it_is_an_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "ws"
            base.mkdir()
            self.assertEqual(first_available_dir(base), base)

    def test_suffixes_past_occupied_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "ws"
            base.mkdir()
            (base / "f.txt").write_text("x", encoding="utf-8")  # ws occupied
            taken1 = base.with_name("ws-1")
            taken1.mkdir()
            (taken1 / "f.txt").write_text("x", encoding="utf-8")  # ws-1 occupied

            self.assertEqual(first_available_dir(base), base.with_name("ws-2"))


class ResolveWorkspaceTargetTests(unittest.TestCase):
    """The CLI-facing rule: in-place when free, else playground / suffixed sibling."""

    def test_explicit_name_used_as_is_when_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            requested = Path(tmpdir) / "myproj"
            resolution = resolve_workspace_target(str(requested))

            self.assertEqual(resolution.project_dir, requested.resolve())
            self.assertIsNone(resolution.relocated_from)

    def test_explicit_name_suffixed_when_occupied(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            requested = Path(tmpdir) / "myproj"
            requested.mkdir()
            (requested / "f.txt").write_text("x", encoding="utf-8")

            resolution = resolve_workspace_target(str(requested))

            self.assertEqual(resolution.project_dir, requested.with_name("myproj-1").resolve())
            self.assertEqual(resolution.relocated_from, requested.resolve())

    def test_no_name_uses_cwd_in_place_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir) / "empty"
            cwd.mkdir()
            with _chdir(cwd):
                resolution = resolve_workspace_target(None)

            self.assertEqual(resolution.project_dir, cwd.resolve())
            self.assertIsNone(resolution.relocated_from)

    def test_no_name_inits_in_place_when_cwd_holds_only_benign(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir) / "git_repo"
            cwd.mkdir()
            (cwd / ".git").mkdir()
            with _chdir(cwd):
                resolution = resolve_workspace_target(None)

            self.assertEqual(resolution.project_dir, cwd.resolve())
            self.assertIsNone(resolution.relocated_from)

    def test_no_name_nests_playground_when_cwd_not_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir) / "busy"
            cwd.mkdir()
            (cwd / "existing.txt").write_text("x", encoding="utf-8")
            with _chdir(cwd):
                resolution = resolve_workspace_target(None)

            self.assertEqual(resolution.project_dir, (cwd / PLAYGROUND_WORKSPACE).resolve())
            self.assertEqual(resolution.relocated_from, cwd.resolve())

    def test_no_name_suffixes_playground_when_it_also_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir) / "busy"
            cwd.mkdir()
            (cwd / "existing.txt").write_text("x", encoding="utf-8")
            playground = cwd / PLAYGROUND_WORKSPACE
            playground.mkdir()
            (playground / "f.txt").write_text("x", encoding="utf-8")  # playground occupied
            with _chdir(cwd):
                resolution = resolve_workspace_target(None)

            self.assertEqual(resolution.project_dir, playground.with_name(f"{PLAYGROUND_WORKSPACE}-1").resolve())
            self.assertEqual(resolution.relocated_from, cwd.resolve())


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
