from __future__ import annotations

import io
import re
import sys
import runpy
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from create_dlthub_workspace.scaffold import SCAFFOLDS_DIR

SCRIPTS = SCAFFOLDS_DIR / "minimal_workspace" / ".scripts"


def _run(script: Path, argv: list[str]):
    """Return (exit_code, stdout, exit_message, browser_mock)."""
    out = io.StringIO()
    code, msg = 0, None
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch("webbrowser.open") as browser,
        redirect_stdout(out),
    ):
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as exc:
            if isinstance(exc.code, int) or exc.code is None:
                code = exc.code or 0
            else:
                code, msg = 1, str(exc.code)
    return code, out.getvalue(), msg, browser


class ScriptsRequireRefTests(unittest.TestCase):
    # Arg-checks run before `import dlt_runtime`, so these work without it installed.
    def test_show_notebook_requires_ref(self) -> None:
        code, _, msg, browser = _run(SCRIPTS / "show_notebook.py", ["show_notebook.py"])
        self.assertEqual(code, 1)
        self.assertIn("usage", (msg or "").lower())
        browser.assert_not_called()

    def test_serve_headless_requires_ref(self) -> None:
        code, _, msg, _ = _run(SCRIPTS / "serve_headless.py", ["serve_headless.py"])
        self.assertEqual(code, 1)
        self.assertIn("usage", (msg or "").lower())


class ExampleJobRefTests(unittest.TestCase):
    def test_scripts_reference_a_deployed_job(self) -> None:
        deployment = (SCAFFOLDS_DIR / "minimal_workspace" / "__deployment__.py").read_text()
        for script in SCRIPTS.glob("*.py"):
            for name in set(re.findall(r"jobs\.([a-z_]+)", script.read_text())):
                self.assertIn(
                    name,
                    deployment,
                    f"{script.name} references jobs.{name}, not deployed in __deployment__.py",
                )


if __name__ == "__main__":
    unittest.main()
