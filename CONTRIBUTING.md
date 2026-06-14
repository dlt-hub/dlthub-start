# Contributing

Thanks for helping improve `dlthub-start`. This project uses a
standard Python `src/` layout, `uv` for environment management, `ruff` for
formatting/linting, and `mypy` for type checking.

The package itself supports Python 3.10+. Generated dltHub workspaces currently
target Python 3.12+ because their scaffold dependencies do.

## Setup

Install development dependencies into a local virtual environment:

```bash
make dev
```

Run the CLI from the checkout:

```bash
uv run dlthub-start --help
```

Create a workspace non-interactively (for tests/CI). `--yes`/`-y` and
`--skip-uv-sync` are hidden testing shortcuts — they cut the guided setup short
(`--yes` skips the prompts and the first run; `--skip-uv-sync` also skips the
dependency sync), so the workspace is scaffolded but not run. Both are
deliberately absent from `--help`; the normal, complete path is interactive
(no flag):

```bash
uv run dlthub-start my-workspace --yes
```

Create a workspace without running the generated workspace dependency sync:

```bash
uv run dlthub-start my-workspace --yes --skip-uv-sync
```

Choose an AI workbench explicitly:

```bash
uv run dlthub-start my-workspace --agent claude
uv run dlthub-start my-workspace --agent claude --agent codex
```

Create a disposable test workspace under `examples/`:

```bash
make workspace
```

The `workspace` target recreates `examples/my-workspace` by default. It
pre-deletes that directory before running the CLI, so only use it for
throwaway local workspaces. To target a different directory:

```bash
make workspace REMOVE_PREV_WORKSPACE=examples/my-demo
```

## Tests

Run the fast unit test suite:

```bash
make test
```

Run the fast end-to-end coverage that avoids a real generated-workspace
dependency sync:

```bash
uv run python -m unittest \
  tests_integration.test_e2e_workspace.WorkspaceCreationFastTests \
  tests_integration.test_e2e_workspace.InstalledEntryPointTests
```

Run all integration tests:

```bash
make test-integration
```

`make test-integration` includes a slow path that invokes the real CLI and runs
`uv sync` in a generated workspace. It may require network access and can take
noticeably longer than the unit suite.

Run a quick bytecode compile check:

```bash
make compile
```

## Quality Checks

Format code:

```bash
make format
```

Run linting and type checks:

```bash
make lint
```

Run the same format/lint/type-check sequence used by CI:

```bash
make lint-ci
```

Run the full local CI workflow:

```bash
make ci
```

`make ci` runs compile checks, linting, unit tests, integration tests, lockfile
drift checks, AI scaffold drift checks, and package build.

## Build

Build the package:

```bash
make build
```

The build artifacts are written to `dist/`.

## AI Workbench Scaffolds

The generated workspace includes vendored dltHub AI workbench files for Claude,
Cursor, and Codex. These files are generated into each bundled scaffold, not
downloaded during normal CLI execution.

The source ref is pinned in `WORKBENCH_REF` in
`src/create_dlthub_workspace/config.py`. To refresh the vendored AI files:

1. Run `make update-ai` to bump `WORKBENCH_REF` to the latest
   `dlt-hub/dlthub-ai-workbench` commit and regenerate the scaffolds. Pass
   `make update-ai REF=<sha>` to pin a specific commit instead.
2. Review the scaffold diff carefully.
3. Run `make check-ai`.
4. Commit the `WORKBENCH_REF` change and regenerated scaffold files together.

`make update-ai` rewrites `WORKBENCH_REF` and then runs `make generate-ai`; if
you only need to regenerate against the already-pinned ref, run `make
generate-ai` directly. `make check-ai` reruns generation and fails if the
committed scaffolds drift from the pinned workbench ref.

## Lockfiles

There are two committed `uv.lock` files: the root project's, and the bundled
workspace scaffold's (`src/create_dlthub_workspace/scaffolds/minimal_workspace/uv.lock`,
shipped so new workspaces install from pinned versions). Each has a symmetric
pair of make targets:

| | Upgrade | Drift check |
|---|---|---|
| Root | `make lock-upgrade` | `make lock-check` |
| Scaffold | `make scaffold-lock-upgrade` | `make scaffold-lock-check` |

- `*-upgrade` re-resolves the lockfile to the newest dependency versions its
  `pyproject.toml` allows. Pass `PKG=<name>` to bump a single package instead of
  everything. Review the diff and commit.
- `*-check` fails if the lockfile is out of sync with its `pyproject.toml`. Both
  checks run in CI and are part of `make ci`; if one fails, run the matching
  `*-upgrade` target and commit.

## Release Checklist

Before publishing, verify:

```bash
uv run dlthub-start --help
make ci
```

The package exposes a single console command:

```text
dlthub-start
```

Then build and publish to PyPI (prompts for a PyPI API token):

```bash
make publish-library
```

