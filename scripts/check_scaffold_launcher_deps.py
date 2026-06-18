"""Verify the bundled minimal workspace declares launcher deps for Batch/Marimo/Dashboard.

Run inside the scaffold venv (``uv run --project <scaffold> python scripts/...``) so
``dlt`` is importable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from packaging.requirements import Requirement

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCAFFOLD = REPO_ROOT / "src/create_dlthub_workspace/scaffolds/minimal_workspace"

# Deduped explicit deps for Batch + Marimo + Dashboard when dlt's API is unavailable.
# Mirrors dlt/_workspace/deployment/requirements.py (dlt 1.28.x). Update when bumping dlt.
MANUAL_REQUIRED_PACKAGES = frozenset(
    {
        "dlt",
        "dlthub",
        "ibis-framework",
        "marimo",
        "pyarrow",
        "s3fs",
    }
)


def _uncovered_via_dlt(scaffold_dir: Path) -> dict[str, list[str]]:
    from dlt._workspace.deployment.launchers import (  # type: ignore[import-not-found]  # noqa: PLC0415
        LAUNCHER_DASHBOARD,
        LAUNCHER_JOB,
        LAUNCHER_MARIMO,
    )
    from dlt._workspace.deployment.requirements import export_workspace_requirements  # type: ignore[import-not-found]  # noqa: PLC0415
    from dlt._workspace.deployment.typing import DASHBOARD_JOB_REF  # type: ignore[import-not-found]  # noqa: PLC0415

    manifest = export_workspace_requirements(scaffold_dir)
    uncovered: dict[str, list[str]] = {}
    for launcher in (LAUNCHER_JOB, LAUNCHER_MARIMO, LAUNCHER_DASHBOARD):
        leftover = manifest["launcher_requirements"].get(launcher, [])
        if leftover:
            uncovered[launcher.rsplit(".", 1)[-1]] = leftover
    dashboard_leftover = manifest["groups"].get(DASHBOARD_JOB_REF, [])
    if dashboard_leftover:
        uncovered["dashboard_group"] = dashboard_leftover
    return uncovered


def check_scaffold_launcher_deps(scaffold_dir: Path = DEFAULT_SCAFFOLD) -> dict[str, list[str]]:
    """Return leftover launcher/dashboard specs not covered by the scaffold pyproject."""
    try:
        return _uncovered_via_dlt(scaffold_dir)
    except Exception as exc:
        print(
            "scaffold-launcher-deps-check: WARNING — dlt launcher-deps API failed "
            f"({exc!r}); falling back to hand-maintained package list.",
            file=sys.stderr,
        )
        return _uncovered_from_manual_list(scaffold_dir)


def _uncovered_from_manual_list(scaffold_dir: Path) -> dict[str, list[str]]:
    doc = tomllib.loads((scaffold_dir / "pyproject.toml").read_text(encoding="utf-8"))
    declared = {
        Requirement(str(dep)).name.replace("_", "-").lower()
        for dep in (doc.get("project", {}) or {}).get("dependencies", []) or []
        if isinstance(dep, str) and dep.strip()
    }
    missing = sorted(pkg for pkg in MANUAL_REQUIRED_PACKAGES if pkg not in declared)
    return {"pyproject": missing} if missing else {}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    scaffold_dir = Path(args[0]).resolve() if args else DEFAULT_SCAFFOLD
    uncovered = check_scaffold_launcher_deps(scaffold_dir)
    if uncovered:
        print(
            f"scaffold-launcher-deps-check: FAILED — {scaffold_dir} pyproject.toml "
            f"does not cover Batch/Marimo/Dashboard launcher deps:",
            file=sys.stderr,
        )
        for key, specs in sorted(uncovered.items()):
            print(f"  {key}: {', '.join(specs)}", file=sys.stderr)
        return 1
    print(f"scaffold-launcher-deps-check: OK — {scaffold_dir} covers launcher deps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
