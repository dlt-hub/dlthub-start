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

Create a workspace with the recommended non-interactive path:

```bash
uv run dlthub-start my-workspace --yes
```

Create a workspace without running the generated workspace dependency sync:

```bash
uv run dlthub-start my-workspace --yes --skip-uv-sync
```

Choose a scaffold or AI workbench explicitly:

```bash
uv run dlthub-start my-workspace --scaffold minimal_workspace
uv run dlthub-start my-workspace --agent claude
uv run dlthub-start my-workspace --agent claude --agent codex
```

Create a disposable test workspace under `examples/`:

```bash
make workspace
```

The `workspace` target recreates `examples/my-workspace` by default. It
pre-deletes that directory before running the CLI, so only use it for
throwaway local workspaces. To choose a different workspace name:

```bash
make workspace TEST_WORKSPACE_NAME=starter-demo
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

`make ci` runs compile checks, linting, unit tests, integration tests, AI
scaffold drift checks, and package build.

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

## Scaffold templates that are gitignored

A few scaffold templates -- notably
`src/create_dlthub_workspace/scaffolds/*/.dlt/secrets.toml` -- are matched by
the scaffold's own `.gitignore` (the one that ships into the user's generated
workspace to keep their real credentials out of git). Because git applies the
*deepest* matching `.gitignore` to a path, that rule also takes effect inside
this repo, and git will normally skip the file.

We want the template tracked here so it ships in the package and reaches every
user. The fix is one-time:

```bash
git add -f src/create_dlthub_workspace/scaffolds/starter_workspace/.dlt/secrets.toml
```

Once tracked, future edits show up in `git diff` like any other file. If you
add a similar tracked-but-ignored scaffold template in the future, do the same.

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

