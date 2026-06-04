"""Bump `WORKBENCH_REF` and regenerate the bundled AI workbench scaffolds.

Run via `make update-ai`. With no argument it resolves the latest commit on the
default branch of `dlt-hub/dlthub-ai-workbench` and pins it; pass an explicit
SHA (`make update-ai REF=<sha>`) to pin a specific commit instead.

Steps:

1. Resolve the target ref (explicit arg, or `git ls-remote ... HEAD`).
2. Rewrite `WORKBENCH_REF` in config.py if it changed.
3. Run `scripts/generate_ai.py` to regenerate every scaffold against the new ref.

Review the resulting diff and commit the `WORKBENCH_REF` bump alongside the
regenerated scaffolds (see CONTRIBUTING.md -> "AI Workbench Scaffolds").
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from create_dlthub_workspace.config import WORKBENCH_REF, WORKBENCH_REPO  # noqa: E402

CONFIG_PATH = REPO_ROOT / "src" / "create_dlthub_workspace" / "config.py"

# Matches the `WORKBENCH_REF: str | None = "..."` (or `= None`) assignment line.
_REF_RE = re.compile(
    r"^(?P<prefix>WORKBENCH_REF:\s*str \| None\s*=\s*).*$",
    re.MULTILINE,
)

_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _resolve_ref(arg: str | None) -> str:
    """Use the explicit arg, or resolve the workbench default branch HEAD."""
    if arg:
        ref = arg.strip()
        if not _SHA_RE.match(ref):
            print(f"error: {ref!r} is not a valid commit SHA", file=sys.stderr)
            raise SystemExit(2)
        return ref

    print(f"Resolving latest commit on {WORKBENCH_REPO} HEAD ...")
    out = subprocess.run(
        ["git", "ls-remote", WORKBENCH_REPO, "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not out:
        print("error: git ls-remote returned no ref", file=sys.stderr)
        raise SystemExit(1)
    return out.split()[0]


def _write_ref(ref: str) -> None:
    content = CONFIG_PATH.read_text(encoding="utf-8")
    new_content, count = _REF_RE.subn(rf'\g<prefix>"{ref}"', content)
    if count != 1:
        print(
            f"error: expected exactly one WORKBENCH_REF assignment, found {count}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    CONFIG_PATH.write_text(new_content, encoding="utf-8")


def main(argv: list[str]) -> int:
    ref = _resolve_ref(argv[0] if argv else None)

    if ref == WORKBENCH_REF:
        print(f"WORKBENCH_REF already at {ref}; regenerating anyway.")
    else:
        print(f"Bumping WORKBENCH_REF: {WORKBENCH_REF or '<none>'} -> {ref}")
        _write_ref(ref)

    print("Running generate_ai.py ...")
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "generate_ai.py")], check=True)
    print("\nDone. Review with `git diff src/create_dlthub_workspace`, then run `make check-ai` before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
