from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from create_dlthub_workspace.errors import UvError
from create_dlthub_workspace.uv import (
    execute_uv_install,
    find_uv,
    run_uv_command,
    run_uv_sync,
)


class UvTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            "VIRTUAL_ENV": "/parent/.venv",
            "CONDA_PREFIX": "/parent/conda",
            "PYTHONPATH": "src",
            "UV_CACHE_DIR": "/tmp/uv-cache",
        },
    )
    @patch("subprocess.run")
    def test_run_uv_sync_drops_parent_python_environment(self, subprocess_run: MagicMock) -> None:
        run_uv_sync("/usr/local/bin/uv", project_dir=Path("/tmp/workspace"))

        env = subprocess_run.call_args.kwargs["env"]
        self.assertNotIn("VIRTUAL_ENV", env)
        self.assertNotIn("CONDA_PREFIX", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertEqual(env["UV_CACHE_DIR"], "/tmp/uv-cache")

    @patch("subprocess.run")
    def test_run_uv_command_executes_in_project_directory(self, subprocess_run: MagicMock) -> None:
        run_uv_command(
            "/usr/local/bin/uv",
            project_dir=Path("/tmp/workspace"),
            args=["run", "dlthub", "--version"],
        )

        subprocess_run.assert_called_once()
        self.assertEqual(subprocess_run.call_args.args[0], ["/usr/local/bin/uv", "run", "dlthub", "--version"])
        self.assertEqual(subprocess_run.call_args.kwargs["cwd"], Path("/tmp/workspace"))

    @patch("create_dlthub_workspace.uv.subprocess.Popen")
    def test_run_uv_command_streams_each_line_to_callback(self, popen: MagicMock) -> None:
        process = popen.return_value
        process.stdout.__enter__.return_value = iter(["loading source\n", "1000 rows\n"])
        process.wait.return_value = 0
        lines: list[str] = []

        run_uv_command(
            "/usr/local/bin/uv",
            project_dir=Path("/tmp/workspace"),
            args=["run", "dlthub", "run", "--follow", "load_sample_shop"],
            stream=True,
            on_line=lines.append,
        )

        # Lines are delivered as they arrive, newline-stripped.
        self.assertEqual(lines, ["loading source", "1000 rows"])
        # The child runs with color disabled so the caller can recolor uniformly.
        self.assertEqual(popen.call_args.kwargs["env"]["NO_COLOR"], "1")
        self.assertIs(popen.call_args.kwargs["stderr"], subprocess.STDOUT)

    @patch("create_dlthub_workspace.uv.subprocess.Popen")
    def test_run_uv_command_stream_raises_on_nonzero_exit(self, popen: MagicMock) -> None:
        process = popen.return_value
        process.stdout.__enter__.return_value = iter(["boom\n"])
        process.wait.return_value = 1

        with self.assertRaises(UvError):
            run_uv_command(
                "/usr/local/bin/uv",
                project_dir=Path("/tmp/workspace"),
                args=["run", "dlthub", "run", "--follow", "load_sample_shop"],
                stream=True,
                on_line=lambda _line: None,
            )


class FindUvTests(unittest.TestCase):
    @patch("create_dlthub_workspace.uv.shutil.which", return_value="/usr/local/bin/uv")
    def test_returns_path_when_uv_is_on_path(self, _which: MagicMock) -> None:
        self.assertEqual(find_uv(), "/usr/local/bin/uv")

    @patch("create_dlthub_workspace.uv.shutil.which", return_value=None)
    def test_falls_back_to_common_install_paths(self, _which: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            candidate = Path(tmpdir) / "uv"
            candidate.touch()
            with patch(
                "create_dlthub_workspace.uv._common_uv_paths",
                return_value=(candidate,),
            ):
                self.assertEqual(find_uv(), str(candidate))

    @patch(
        "create_dlthub_workspace.uv._common_uv_paths",
        return_value=(Path("/nonexistent/uv"),),
    )
    @patch("create_dlthub_workspace.uv.shutil.which", return_value=None)
    def test_returns_none_when_uv_absent_everywhere(
        self,
        _which: MagicMock,
        _paths: MagicMock,
    ) -> None:
        self.assertIsNone(find_uv())


class ExecuteUvInstallTests(unittest.TestCase):
    @patch("create_dlthub_workspace.uv.find_uv", return_value="/usr/local/bin/uv")
    @patch("create_dlthub_workspace.uv.install_uv")
    def test_returns_path_when_uv_is_findable_after_install(
        self,
        install_uv: MagicMock,
        _find_uv: MagicMock,
    ) -> None:
        self.assertEqual(execute_uv_install(), "/usr/local/bin/uv")
        install_uv.assert_called_once()

    @patch("create_dlthub_workspace.uv.find_uv", return_value=None)
    @patch("create_dlthub_workspace.uv.install_uv")
    def test_raises_uv_error_when_uv_still_missing_after_install(
        self,
        _install_uv: MagicMock,
        _find_uv: MagicMock,
    ) -> None:
        with self.assertRaises(UvError):
            execute_uv_install()


class RunUvSubprocessFailureTests(unittest.TestCase):
    @patch("subprocess.run")
    def test_run_uv_sync_raises_uv_error_on_subprocess_failure(
        self,
        subprocess_run: MagicMock,
    ) -> None:
        subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["uv", "sync"],
            stderr=b"resolution failed: package not found",
        )

        with self.assertRaises(UvError) as cm:
            run_uv_sync("/usr/local/bin/uv", project_dir=Path("/tmp/workspace"))

        self.assertIn("exit code 1", str(cm.exception))
        self.assertIn("resolution failed", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
