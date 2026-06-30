from __future__ import annotations

import json
import py_compile
import sys
import tempfile
import unittest
from pathlib import Path

from create_dlthub_workspace.scaffold import SCAFFOLDS_DIR, copy_scaffold

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

WORKSPACE = SCAFFOLDS_DIR / "minimal_workspace"
NOTEBOOK = WORKSPACE / "notebooks" / "onboarding_success"
SNAPSHOT = NOTEBOOK / "__marimo__" / "session" / "onboarding_success.py.json"


def _locked_version(package: str) -> str:
    lock = tomllib.loads((WORKSPACE / "uv.lock").read_text())
    return next(p["version"] for p in lock["package"] if p["name"] == package)


class SessionSnapshotTests(unittest.TestCase):
    def test_snapshot_exists_and_is_valid_json(self) -> None:
        self.assertTrue(SNAPSHOT.is_file(), "session snapshot should ship with the scaffold")
        json.loads(SNAPSHOT.read_text())  # raises on invalid JSON

    def test_snapshot_marimo_version_matches_lock(self) -> None:
        # A mismatch silently disables the cache on deploy (key includes the version).
        snap = json.loads(SNAPSHOT.read_text())
        self.assertEqual(snap["metadata"]["marimo_version"], _locked_version("marimo"))

    def test_snapshot_has_no_inlined_anywidget_module(self) -> None:
        # A cached anywidget ESM becomes a data: URL the frontend refuses to load.
        self.assertNotIn("data:text/javascript", SNAPSHOT.read_text())


class NotebookWiringTests(unittest.TestCase):
    def test_deployment_deploys_the_notebook(self) -> None:
        self.assertIn("onboarding_success", (WORKSPACE / "__deployment__.py").read_text())

    def test_shipped_python_files_compile(self) -> None:
        files = [*NOTEBOOK.rglob("*.py"), *(WORKSPACE / ".scripts").glob("*.py")]
        self.assertTrue(files)
        for path in files:
            py_compile.compile(str(path), doraise=True)


class ScaffoldShipsNotebookTests(unittest.TestCase):
    def test_copy_scaffold_ships_notebook_and_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            copy_scaffold(ws, scaffold="minimal_workspace", agent="claude")
            for rel in (
                "notebooks/onboarding_success/onboarding_success.py",
                "notebooks/onboarding_success/__marimo__/session/onboarding_success.py.json",
                ".scripts/serve_headless.py",
                ".scripts/show_notebook.py",
            ):
                self.assertTrue((ws / rel).exists(), f"{rel!r} should be scaffolded")


if __name__ == "__main__":
    unittest.main()
