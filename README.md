# dlthub-start (beta)

Create a ready-to-run dltHub workspace with example pipelines, local `uv`
dependency setup, and bundled dltHub AI workbench files.

## Quickstart

`uvx` is the recommended way to run the CLI:

```bash
uvx dlthub-start@latest my-workspace
```

If `uvx` is not available yet, use `pipx run` instead:

```bash
pipx run dlthub-start my-workspace
```

The CLI prompts for a scaffold and AI workbench files, checks for `uv`, offers
to install it if needed, offers to run `uv sync`, and prints next steps.

For a non-interactive setup with the recommended defaults:

```bash
uvx dlthub-start@latest my-workspace --yes
cd my-workspace
uv run dlthub run load_breweries
uv run dlthub show
```

Both `uvx` and `pipx run` work. If the generated workspace needs `uv` and it is
not installed yet, the CLI will offer to install it for you. If you prefer to
install `uv` yourself, use the official
[`uv` installation guide](https://docs.astral.sh/uv/getting-started/installation/).

## What You Get

- A Python dltHub workspace with project metadata customized to your directory name.
- A bundled scaffold copied from this package, not downloaded at create time.
- dltHub AI workbench files for your chosen coding agent (Claude, Cursor, or Codex).
- Shared dltHub AI toolkit files for data exploration, runtime deployment, REST API pipeline work, and transformations.
- A local DuckDB-backed warehouse configuration for quick first runs.

## Usage

```bash
uvx dlthub-start@latest [project-dir] [options]
```

Initializes a workspace **in place**: the current directory by default, or
`project-dir` if given. Either way the target directory must be **empty**
(hidden entries like `.git` and `.gitignore` count) — otherwise the command
stops with guidance and does nothing.

Common options:

| Option | Description |
| --- | --- |
| `--yes`, `-y` | Use the recommended path: the recommended scaffold, the Claude workbench, install `uv` if missing, and run `uv sync`. |
| `--scaffold starter_workspace` | Create the full starter workspace. This is the default recommended scaffold. |
| `--scaffold minimal_workspace` | Create a small workspace with one placeholder pipeline. |
| `--agent claude` | Use the Claude workbench files. Choose exactly one agent (`claude`, `cursor`, or `codex`); defaults to `claude`. |
| `--agent cursor` | Use the Cursor workbench files. |
| `--agent codex` | Use the Codex workbench files. |
| `--skip-uv-sync` | Create the scaffold and selected AI files, but stop before installing workspace dependencies. |
| `--verbose`, `-v` | Stream output from underlying subprocesses. |

Examples:

```bash
uvx dlthub-start@latest --yes                            # initialize in the current (empty) directory
uvx dlthub-start@latest my-workspace --yes               # create and initialize ./my-workspace
uvx dlthub-start@latest my-workspace --scaffold minimal_workspace
uvx dlthub-start@latest my-workspace --agent codex
uvx dlthub-start@latest my-workspace --yes --skip-uv-sync
```

## Scaffolds

| Scaffold | Best For | Contents |
| --- | --- | --- |
| `starter_workspace` | Exploring the full dltHub workflow quickly. | Open Brewery DB ingestion, Ibis transformations, scheduled data quality checks, marimo notebooks, and a generated deployment module. |
| `minimal_workspace` | Starting from a clean, small project. | One placeholder dlt pipeline, local warehouse config, and generated deployment module. |

## Generated Workspace

The starter scaffold creates a workspace shaped roughly like this:

```text
my-workspace/
|-- pyproject.toml
|-- uv.lock
|-- starter_pipeline.py
|-- starter_transformations.py
|-- starter_data_quality.py
|-- __deployment__.py
|-- notebooks/
|-- .dlt/
|-- .agents/
|-- .claude/        # when Claude is selected
|-- .cursor/        # when Cursor is selected
`-- .codex/         # when Codex is selected
```

The minimal scaffold uses `pipeline.py` instead of the starter example modules.

## Next Steps

For the starter scaffold:

```bash
cd my-workspace
uv run dlthub run load_breweries
uv run dlthub show
```

For the minimal scaffold:

```bash
cd my-workspace
uv run dlthub run load_data
uv run dlthub show
```

If you created the workspace with `--skip-uv-sync`, finish setup first:

```bash
cd my-workspace
uv sync
```

## Troubleshooting

`uvx: command not found`

Use `pipx run dlthub-start my-workspace` instead. The CLI will still
offer to install `uv` before syncing the generated workspace dependencies.

`Target directory already exists and is not empty`

Choose a new directory or empty the existing one. The CLI will not overwrite a
non-empty workspace directory.

`uv sync` fails

Re-run with `--verbose` to see subprocess output:

```bash
uvx dlthub-start@latest my-workspace --yes --verbose
```

If the scaffold was created successfully, you can also enter the workspace and
run `uv sync` directly after fixing the underlying dependency or network issue.

## Development

For local setup, tests, build commands, `make workspace`, and AI workbench
scaffold regeneration, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Publishing

To build and publish a release to PyPI:

```bash
make publish-library
```

This removes any previous `dist/` artifacts, builds the package with
`uv build`, lists the artifacts, and prompts for a PyPI API token before
uploading with `uv publish`. Before publishing, run the release checklist in
[CONTRIBUTING.md](CONTRIBUTING.md) and make sure the version in
`pyproject.toml` has been bumped.
