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

Create a workspace non-interactively (for tests/CI). `--setup-only` and
`--scaffold-only` are hidden testing shortcuts that cut the guided setup short —
both skip login, playground connection, and the agent hand-off. `--setup-only`
still installs dependencies (and uses the default agent); `--scaffold-only` stops
right after scaffolding, before the dependency sync. Both are deliberately absent
from `--help`; the normal, complete path is interactive (no flag):

```bash
uv run dlthub-start my-workspace --setup-only
```

Create a workspace without installing the generated workspace's dependencies:

```bash
uv run dlthub-start my-workspace --scaffold-only
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
make workspace WORKSPACE_DIR=examples/my-demo
```

### Testing against dev/local runtime stacks

`make workspace` targets prod (the released `dlthub-client` from PyPI). To scaffold
a throwaway workspace pointed at a non-prod runtime instead:

| Target | Stack | Notes |
|---|---|---|
| `make workspace-dev` | `api.dlthub.dev` | editable `dlthub-client` from a local checkout |
| `make workspace-local` | `api.dlthub.test` (+ `auth.dlthub.test`) | editable client; skips TLS verify (mkcert CA isn't in Python's bundle) |
| `make workspace-stage` | `api.dlthub.net` | released client |

`workspace-dev`/`workspace-local` pin the stack's `api_base_url` (and, for local,
`auth_base_url` — it sits on its own host) into the workspace's `.dlt/config.toml`
at scaffold time via the CLI's `--api-base-url` / `--auth-base-url` flags. They also
point `dlthub-client` at a local runtime checkout (editable, via
`--dlthub-client-source`) so the client matches an API that may be ahead of the
released package. The checkout defaults to the sibling `../runtime/clients/cli`;
override it:

```bash
DLTHUB_CLIENT_SOURCE=/path/to/runtime/clients/cli make workspace-dev
```

When running `dlthub` commands **by hand** in a local workspace, set
`DLT_RUNTIME_INSECURE=true` (the mkcert cert isn't in Python's trust bundle), e.g.
`DLT_RUNTIME_INSECURE=true uv run dlthub login`. Browser login against the local
stack also needs the runtime's mock host resolvable — add `127.0.0.1 dev-mock-services`
to `/etc/hosts`.

## Telemetry

The CLI sends anonymous usage events to PostHog. Users opt out with `--no-telemetry`,
`DLTHUB_START_TELEMETRY=0`, or `DO_NOT_TRACK=1`, and an existing dlt opt-out
(`runtime.dlthub_telemetry = false` in dlt's global `config.toml`, or
`RUNTIME__DLTHUB_TELEMETRY=0`) is honored.

For development and testing, three environment variables override the defaults:

| Variable | Effect |
|---|---|
| `DLTHUB_START_TELEMETRY` | Force telemetry on (`1`/`true`/`yes`/`on`) or off (any other value). |
| `DLTHUB_START_POSTHOG_KEY` | Override the bundled PostHog project key. |
| `DLTHUB_START_POSTHOG_HOST` | Override the PostHog host (default `https://eu.i.posthog.com`). |

Released builds bake the project key into a gitignored `_telemetry_key.py`; a dev
checkout has no key, so telemetry stays disabled until you set
`DLTHUB_START_POSTHOG_KEY`. To exercise the full path against a throwaway PostHog
project:

```bash
DLTHUB_START_TELEMETRY=1 \
DLTHUB_START_POSTHOG_KEY=phc_your_test_key \
DLTHUB_START_POSTHOG_HOST=https://eu.i.posthog.com \
  uv run dlthub-start my-workspace --setup-only
```

For releases, put the real key in a gitignored `.make.env`
(`DLTHUB_START_POSTHOG_KEY=phc_...`); the Makefile loads it into `uv build`, and
`make publish` refuses to run without it.

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

### Asserting on rendered output

`display.console` is a plain `Console()` that auto-detects color from stdout, so
captured panel output is plain text when piped (CI) but carries ANSI styling and
wraps to the terminal width in an interactive shell. A test that asserts on
`console.capture()` output without normalizing will pass in one environment and
fail in the other. Use `_panel_text()` in `tests/test_display.py` — it strips ANSI
styling and panel borders and collapses whitespace, so substring checks don't
depend on color or terminal width.

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

Bump the version — this rewrites `pyproject.toml` and `uv.lock` together.
`config.VERSION` is read from package metadata, so the version in `pyproject.toml`
is the single source; nothing else needs editing.

```bash
make version-upgrade          # prompts for major / minor / patch
make version-upgrade-patch    # non-interactive (also -minor / -major)
```

`version-upgrade` prompts interactively; the `version-upgrade-{patch,minor,major}`
variants (or `make version-upgrade LEVEL=patch`) are non-interactive for CI/agents.

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
make publish
```

