"""Tests for scripts/check_scaffold_launcher_deps.py."""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECK_SCRIPT = REPO_ROOT / "scripts/check_scaffold_launcher_deps.py"


def _load_check_module():
    spec = importlib.util.spec_from_file_location("check_scaffold_launcher_deps", CHECK_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_pyproject(project_dir: Path, dependencies: list[str]) -> None:
    lines = [
        "[project]",
        'name = "test-workspace"',
        'version = "0.1.0"',
        "dependencies = [",
        *(f'    "{dep}",' for dep in dependencies),
        "]",
    ]
    (project_dir / "pyproject.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_dlt_failure_falls_back_to_manual_list_with_warning() -> None:
    check = _load_check_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        _write_pyproject(project_dir, ["dlt[hub]>=1.0", "dlthub", "marimo", "pyarrow", "ibis-framework"])
        stderr = io.StringIO()
        with (
            patch.object(check, "_uncovered_via_dlt", side_effect=ImportError("no dlt")),
            patch.object(sys, "stderr", stderr),
        ):
            uncovered = check.check_scaffold_launcher_deps(project_dir)
    assert uncovered == {"pyproject": ["s3fs"]}
    assert "WARNING" in stderr.getvalue()
    assert "falling back to hand-maintained package list" in stderr.getvalue()


def test_manual_list_passes_when_all_required_packages_declared() -> None:
    check = _load_check_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        _write_pyproject(
            project_dir,
            [
                "dlt[hub]>=1.0",
                "dlthub[mcp]",
                "marimo>=0.23",
                "pyarrow>=24",
                "ibis-framework[duckdb]>=12",
                "s3fs",
            ],
        )
        with patch.object(check, "_uncovered_via_dlt", side_effect=RuntimeError("dlt api broke")):
            uncovered = check.check_scaffold_launcher_deps(project_dir)
    assert uncovered == {}


def test_manual_list_fails_when_required_package_missing() -> None:
    check = _load_check_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        _write_pyproject(project_dir, ["dlt[hub]>=1.0", "dlthub", "marimo", "pyarrow", "ibis-framework"])
        with patch.object(check, "_uncovered_via_dlt", side_effect=ImportError("no dlt")):
            uncovered = check.check_scaffold_launcher_deps(project_dir)
    assert uncovered == {"pyproject": ["s3fs"]}


def test_dlt_path_fails_when_export_reports_missing_launcher_deps() -> None:
    check = _load_check_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        _write_pyproject(project_dir, ["dlt[hub]>=1.0"])
        with patch.object(
            check,
            "_uncovered_via_dlt",
            return_value={"job": ["botocore", "s3fs"], "dashboard_group": ["s3fs"]},
        ):
            uncovered = check.check_scaffold_launcher_deps(project_dir)
    assert uncovered == {"job": ["botocore", "s3fs"], "dashboard_group": ["s3fs"]}


def test_dlt_path_passes_when_export_reports_no_missing_deps() -> None:
    check = _load_check_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        _write_pyproject(project_dir, ["dlt[hub]>=1.0", "s3fs"])
        with patch.object(check, "_uncovered_via_dlt", return_value={}):
            uncovered = check.check_scaffold_launcher_deps(project_dir)
    assert uncovered == {}


def test_main_exits_nonzero_when_deps_missing() -> None:
    check = _load_check_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        _write_pyproject(project_dir, ["dlt[hub]>=1.0"])
        with patch.object(check, "check_scaffold_launcher_deps", return_value={"job": ["s3fs"]}):
            exit_code = check.main([str(project_dir)])
    assert exit_code == 1


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str) -> unittest.TestSuite:
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            tests.addTest(unittest.FunctionTestCase(obj))
    return tests
