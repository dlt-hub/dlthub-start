"""Tests for display panels (next-steps + resume-steps + banner).

Uses `console.capture()` to grab rendered text so we can assert on
the content of rich panels.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from create_dlthub_workspace.config import VERSION
from create_dlthub_workspace.display import (
    CREATED_TREE,
    NEXT_STEPS,
    NEXT_STEPS_AFTER_RUN,
    _cd_target,
    console,
    print_banner,
    print_next_steps,
    print_resume_steps,
)
from create_dlthub_workspace.scaffold import SCAFFOLDS_DIR


class PrintNextStepsTests(unittest.TestCase):
    def test_minimal_scaffold_renders_with_its_pipeline_command(self) -> None:
        with console.capture() as cap:
            print_next_steps(Path("/tmp/my_workspace"), scaffold="minimal_workspace")
        output = cap.get()

        self.assertIn("Created", output)
        self.assertIn("pipeline.py", output)
        self.assertNotIn("starter_pipeline.py", output)
        self.assertIn("uv run dlthub run load_sample_shop", output)
        # Minimal scaffold has an instruction-only step with no command.
        self.assertIn("Edit pipeline.py", output)

    def test_first_pipeline_ran_shows_build_own_source_step(self) -> None:
        # When the first pipeline was already run during setup, the panel drops
        # the run / view-runs steps (they just happened) and points the user at
        # building a pipeline for their own source.
        with console.capture() as cap:
            print_next_steps(Path.cwd(), scaffold="minimal_workspace", first_pipeline_ran=True)
        output = cap.get()

        self.assertNotIn("uv run dlthub run load_sample_shop", output)
        self.assertNotIn("job runs show", output)
        self.assertIn("Build a pipeline", output)

    def test_renders_selected_agent(self) -> None:
        with console.capture() as cap:
            print_next_steps(Path("/tmp/my_workspace"), scaffold="minimal_workspace", agent="claude")
        output = cap.get()

        self.assertIn("Coding agent", output)
        self.assertIn("claude", output)

    def test_unknown_scaffold_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            print_next_steps(Path("/tmp/my_workspace"), scaffold="bogus")

    def test_cd_step_uses_relative_path_for_workspace_under_cwd(self) -> None:
        # A workspace created under the cwd should render a short, relative
        # `cd` so the command is copy-pasteable from where the user ran us.
        project_dir = Path.cwd() / "hello-world"
        with console.capture() as cap:
            print_next_steps(project_dir, scaffold="minimal_workspace")
        output = cap.get()

        self.assertIn("cd hello-world", output)
        self.assertNotIn(f"cd {project_dir}", output)

    def test_cd_step_omitted_when_target_is_cwd(self) -> None:
        # Init-in-place: the workspace is the current directory, so there's
        # nothing to cd into and the step should not render.
        with console.capture() as cap:
            print_next_steps(Path.cwd(), scaffold="minimal_workspace")
        output = cap.get()

        self.assertNotIn("cd ", output)
        # The actual first step (the pipeline run) is still present.
        self.assertIn("uv run dlthub run load_sample_shop", output)

    def test_agent_workspace_note_shown_only_for_subdir(self) -> None:
        # Subdir → note reminds AI agents to work from the workspace root.
        with console.capture() as cap:
            print_next_steps(Path.cwd() / "hello-world", scaffold="minimal_workspace")
        self.assertIn("Note for AI agents", cap.get())

        # Init-in-place (cwd) → no note; the agent is already at the root.
        with console.capture() as cap:
            print_next_steps(Path.cwd(), scaffold="minimal_workspace")
        self.assertNotIn("Note for AI agents", cap.get())


class CdTargetTests(unittest.TestCase):
    def test_relative_when_directly_under_cwd(self) -> None:
        self.assertEqual(_cd_target(Path.cwd() / "hello-world"), "hello-world")

    def test_relative_for_nested_path_under_cwd(self) -> None:
        target = Path.cwd() / "nested" / "hello-world"
        self.assertEqual(_cd_target(target), os.path.join("nested", "hello-world"))

    def test_absolute_when_outside_cwd(self) -> None:
        # A sibling of the cwd would relativize to "../..", so we keep it
        # absolute instead of printing an ugly traversal.
        outside = Path.cwd().parent / "outside-xyz" / "hello-world"
        self.assertEqual(_cd_target(outside), str(outside))


class CreatedTreeTests(unittest.TestCase):
    def test_created_tree_entries_exist_in_bundled_scaffolds(self) -> None:
        for scaffold, entries in CREATED_TREE.items():
            with self.subTest(scaffold=scaffold):
                scaffold_dir = SCAFFOLDS_DIR / scaffold
                self.assertTrue(scaffold_dir.is_dir())
                for entry in entries:
                    normalized = entry.rstrip("/")
                    self.assertTrue(
                        (scaffold_dir / normalized).exists(),
                        f"{entry!r} is shown in the success panel but is missing from {scaffold}",
                    )

    def test_created_tree_covers_every_next_steps_scaffold(self) -> None:
        # If a scaffold can render next steps, it should also render a matching
        # "Created" tree and a post-run step list (used when the first pipeline
        # was run during setup).
        self.assertEqual(set(CREATED_TREE), set(NEXT_STEPS))
        self.assertEqual(set(NEXT_STEPS_AFTER_RUN), set(NEXT_STEPS))


class PrintResumeStepsTests(unittest.TestCase):
    def test_uv_not_installed_includes_install_command(self) -> None:
        with console.capture() as cap:
            print_resume_steps(Path("/tmp/my_workspace"), uv_installed=False)
        output = cap.get()

        self.assertIn("Install uv", output)
        self.assertIn("curl -LsSf https://astral.sh/uv/install.sh", output)
        self.assertIn("uv sync", output)

    def test_uv_installed_omits_install_command(self) -> None:
        with console.capture() as cap:
            print_resume_steps(Path("/tmp/my_workspace"), uv_installed=True)
        output = cap.get()

        self.assertNotIn("curl -LsSf", output)
        self.assertIn("uv sync", output)


class PrintBannerTests(unittest.TestCase):
    def test_renders_with_version_in_title(self) -> None:
        with console.capture() as cap:
            print_banner()
        output = cap.get()

        self.assertIn(f"v{VERSION}", output)

    def test_renders_beta_tag_next_to_version(self) -> None:
        with console.capture() as cap:
            print_banner()
        output = cap.get()

        self.assertIn("(beta)", output)


if __name__ == "__main__":
    unittest.main()
