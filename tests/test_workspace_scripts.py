from __future__ import annotations

import io
import os
import re
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from create_dlthub_workspace.scaffold import SCAFFOLDS_DIR

SCRIPTS = SCAFFOLDS_DIR / "minimal_workspace" / ".scripts"


def _run(script: Path, argv: list[str], app_url: str | None = None):
    """Return (exit_code, stdout, exit_message, browser_mock)."""
    env = dict(os.environ)
    if app_url is None:
        env.pop("DLTHUB_APP_URL", None)
    else:
        env["DLTHUB_APP_URL"] = app_url
    out = io.StringIO()
    code, msg = 0, None
    with (
        mock.patch.object(sys, "argv", argv),
        mock.patch.dict(os.environ, env, clear=True),
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


def _workspace_with_config(tmp: Path, body: str) -> Path:
    (tmp / ".dlt").mkdir(parents=True)
    (tmp / ".dlt" / "config.toml").write_text(body)
    (tmp / ".scripts").mkdir()
    for name in ("show_notebook.py", "serve_headless.py"):
        (tmp / ".scripts" / name).write_text((SCRIPTS / name).read_text())
    return tmp


class ScriptsRequireRefTests(unittest.TestCase):
    def test_show_notebook_requires_ref(self) -> None:
        code, _, msg, browser = _run(SCRIPTS / "show_notebook.py", ["show_notebook.py"])
        self.assertEqual(code, 1)
        self.assertIn("usage", (msg or "").lower())
        browser.assert_not_called()

    def test_serve_headless_requires_ref(self) -> None:
        # Arg-check runs before `import dlt_runtime`, so this works without it installed.
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


class ShowNotebookUrlTests(unittest.TestCase):
    CONFIG = '[runtime]\nworkspace_id = "ws-123"\n'

    def test_builds_show_url_and_opens_browser(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = _workspace_with_config(Path(d), self.CONFIG)
            code, out, _, browser = _run(
                ws / ".scripts" / "show_notebook.py", ["show_notebook.py", "jobs.onboarding_success"]
            )
        url = "https://app.dlthub.com/w/ws-123/notebooks/jobs.onboarding_success/show?hide_header=true"
        self.assertEqual(code, 0)
        self.assertIn(url, out)
        browser.assert_called_once_with(url)

    def test_derives_app_base_from_pinned_api_base_url(self) -> None:
        for api_base, app_base in (
            ("https://api.dlthub.test", "https://dlthub.test"),
            ("https://api.dlthub.dev", "https://app.dlthub.dev"),
        ):
            with self.subTest(api_base=api_base), tempfile.TemporaryDirectory() as d:
                config = self.CONFIG + f'api_base_url = "{api_base}"\n'
                ws = _workspace_with_config(Path(d), config)
                code, out, _, _ = _run(
                    ws / ".scripts" / "show_notebook.py", ["show_notebook.py", "jobs.onboarding_success"]
                )
            self.assertEqual(code, 0)
            self.assertIn(f"{app_base}/w/ws-123/", out)

    def test_app_url_override_beats_pinned_api_base_url(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            config = self.CONFIG + 'api_base_url = "https://api.dlthub.dev"\n'
            ws = _workspace_with_config(Path(d), config)
            code, out, _, browser = _run(
                ws / ".scripts" / "show_notebook.py",
                ["show_notebook.py", "jobs.onboarding_success"],
                app_url="https://dlthub.test/",
            )
        self.assertEqual(code, 0)
        self.assertIn("https://dlthub.test/w/ws-123/", out)

    def test_errors_when_workspace_id_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = _workspace_with_config(Path(d), '[runtime]\nlog_level = "INFO"\n')
            code, _, msg, browser = _run(
                ws / ".scripts" / "show_notebook.py", ["show_notebook.py", "jobs.onboarding_success"]
            )
        self.assertEqual(code, 1)
        self.assertIn("workspace_id", msg or "")
        browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()
