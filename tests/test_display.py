"""Tests for display panels (next-steps + resume-steps + banner).

Uses `console.capture()` to grab rendered text so we can assert on
the content of rich panels.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from create_dlthub_workspace.config import VERSION
from create_dlthub_workspace.display import (
    CREATED_TREE,
    NEXT_STEPS,
    console,
    print_banner,
    print_next_steps,
    print_resume_steps,
)
from create_dlthub_workspace.scaffold import SCAFFOLDS_DIR


class PrintNextStepsTests(unittest.TestCase):
    def test_starter_scaffold_renders_and_includes_cd_hint(self) -> None:
        project_dir = Path("/tmp/my_workspace")
        with console.capture() as cap:
            print_next_steps(project_dir, scaffold="starter_workspace")
        output = cap.get()

        # str(path) so the assertion matches the platform's separator
        # (Windows renders backslashes, POSIX renders forward slashes).
        self.assertIn(str(project_dir), output)
        self.assertIn("Created", output)
        self.assertIn("starter_pipeline.py", output)
        self.assertIn("starter_transformations.py", output)
        self.assertIn(".agents/", output)
        self.assertIn("prod.secrets.toml", output)
        self.assertIn("database name and token", output)
        self.assertIn("uv run dlthub run load_breweries", output)

    def test_minimal_scaffold_renders_with_its_pipeline_command(self) -> None:
        with console.capture() as cap:
            print_next_steps(Path("/tmp/my_workspace"), scaffold="hello_world_workspace")
        output = cap.get()

        self.assertIn("Created", output)
        self.assertIn("pipeline.py", output)
        self.assertNotIn("starter_pipeline.py", output)
        self.assertIn("uv run dlthub run load_data", output)
        # Minimal scaffold has an instruction-only step with no command.
        self.assertIn("Edit pipeline.py", output)

    def test_renders_selected_ai_workbenches(self) -> None:
        with console.capture() as cap:
            print_next_steps(Path("/tmp/my_workspace"), scaffold="starter_workspace", agents=("claude", "codex"))
        output = cap.get()

        self.assertIn("AI workbenches", output)
        self.assertIn("claude, codex", output)

    def test_unknown_scaffold_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            print_next_steps(Path("/tmp/my_workspace"), scaffold="bogus")


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
        # "Created" tree.
        self.assertEqual(set(CREATED_TREE), set(NEXT_STEPS))


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
