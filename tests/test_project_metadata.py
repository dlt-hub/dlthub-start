from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from create_dlthub_workspace.errors import ScaffoldError
from create_dlthub_workspace.project_metadata import (
    apply_dlthub_client_source,
    apply_runtime_base_urls,
    apply_workspace_name,
    normalize_project_name,
)


class ProjectMetadataTests(unittest.TestCase):
    def test_normalize_project_name(self) -> None:
        self.assertEqual(normalize_project_name("My Workspace"), "my-workspace")
        self.assertEqual(normalize_project_name("github_ingest_workspace"), "github-ingest-workspace")
        self.assertEqual(normalize_project_name("___"), "dlthub-workspace")

    def test_apply_workspace_name_rewrites_project_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text(
                '[project]\nname = "github-ingest-workspace"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

            package_name = apply_workspace_name(project_dir, "My Workspace")

            self.assertEqual(package_name, "my-workspace")
            self.assertIn('name = "my-workspace"', pyproject.read_text(encoding="utf-8"))

    def test_apply_workspace_name_inserts_missing_project_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")

            apply_workspace_name(project_dir, "New Workspace")

            self.assertIn('name = "new-workspace"', pyproject.read_text(encoding="utf-8"))

    def test_apply_workspace_name_raises_on_malformed_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text("this is not valid toml [[[", encoding="utf-8")

            with self.assertRaises(ScaffoldError):
                apply_workspace_name(project_dir, "any-name")

    def test_apply_workspace_name_renames_lock_root_in_lockstep(self) -> None:
        # The renamed project name MUST be mirrored into uv.lock's virtual root
        # package. Otherwise uv considers the lock stale, re-resolves against the
        # PyPI index, and the bundled lock provides no benefit. Only the virtual
        # root entry is renamed; a dependency that happens to share the old name
        # and the inline `{ name = ... }` references are left untouched.
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").write_text(
                '[project]\nname = "dlthub-minimal-workspace"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            lock = project_dir / "uv.lock"
            lock.write_text(
                "version = 1\nrevision = 3\n\n"
                "[[package]]\n"
                'name = "dlthub-minimal-workspace"\n'
                'version = "0.1.0"\n'
                'source = { virtual = "." }\n'
                "dependencies = [\n"
                '    { name = "dlthub-minimal-workspace-dep" },\n'
                "]\n\n"
                "[[package]]\n"
                'name = "some-dep"\n'
                'version = "1.2.3"\n'
                'source = { registry = "https://pypi.org/simple" }\n',
                encoding="utf-8",
            )

            apply_workspace_name(project_dir, "My Workspace")

            lock_text = lock.read_text(encoding="utf-8")
            # Virtual root renamed...
            self.assertIn(
                'name = "my-workspace"\nversion = "0.1.0"\nsource = { virtual = "." }',
                lock_text,
            )
            # ...and nothing else in the lock still carries the old root name,
            # while the unrelated registry dependency is preserved verbatim.
            self.assertNotIn('name = "dlthub-minimal-workspace"', lock_text)
            self.assertIn('{ name = "dlthub-minimal-workspace-dep" }', lock_text)
            self.assertIn('name = "some-dep"', lock_text)

    def test_apply_workspace_name_without_lockfile_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").write_text(
                '[project]\nname = "dlthub-minimal-workspace"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

            # No uv.lock present: rename must succeed without raising.
            apply_workspace_name(project_dir, "My Workspace")

            self.assertFalse((project_dir / "uv.lock").exists())


class RuntimeBaseUrlsTests(unittest.TestCase):
    def test_pins_both_base_urls_under_runtime(self) -> None:
        # Mirrors the real scaffold (a [runtime] table, no base URLs) and the
        # local case that needs both api and a split-out auth host.
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            config_path = project_dir / ".dlt" / "config.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text('[runtime]\nlog_level="WARNING"\n', encoding="utf-8")

            apply_runtime_base_urls(
                project_dir,
                api_base_url="https://api.dlthub.test",
                auth_base_url="https://auth.dlthub.test",
            )

            text = config_path.read_text(encoding="utf-8")
            self.assertIn('api_base_url = "https://api.dlthub.test"', text)
            self.assertIn('auth_base_url = "https://auth.dlthub.test"', text)
            self.assertIn('log_level="WARNING"', text)


class DlthubClientSourceTests(unittest.TestCase):
    def test_adds_dependency_and_editable_source(self) -> None:
        # Mirrors the real scaffold: a dependencies array + an empty [tool.uv.sources].
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "ws"
            project_dir.mkdir()
            (project_dir / "pyproject.toml").write_text(
                '[project]\nname = "ws"\ndependencies = [\n    "dlthub[mcp]",\n]\n\n[tool.uv.sources]\n',
                encoding="utf-8",
            )
            # The source must be a real path containing a pyproject.toml.
            client_src = Path(tmpdir) / "clients" / "cli"
            client_src.mkdir(parents=True)
            (client_src / "pyproject.toml").write_text('[project]\nname = "dlthub-client"\n', encoding="utf-8")

            apply_dlthub_client_source(project_dir, str(client_src))

            text = (project_dir / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn('"dlthub-client",', text)
            self.assertIn(f'dlthub-client = {{ path = "{client_src.resolve()}", editable = true }}', text)

    def test_missing_source_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").write_text("[project]\ndependencies = [\n]\n", encoding="utf-8")

            with self.assertRaises(ScaffoldError):
                apply_dlthub_client_source(project_dir, str(Path(tmpdir) / "does-not-exist"))


if __name__ == "__main__":
    unittest.main()
