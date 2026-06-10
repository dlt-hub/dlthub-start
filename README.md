# dlthub-start (beta)

Create a ready-to-run dltHub workspace with example pipelines, local `uv`
dependency setup, and bundled dltHub AI workbench files.

## Quickstart

`uvx` is the recommended way to run the CLI. Run it from inside an empty
project directory so the AI workbench files (skills + MCP server) land at the
**project root**, where your coding agent runs:

```bash
mkdir my-workspace && cd my-workspace
uvx dlthub-start@latest
```

No `uv`? Install the CLI with pip (into your current Python environment) and
run it directly:

```bash
pip install dlthub-start
dlthub-start
```

The CLI prompts for your coding agent, checks for `uv` (offering to install it
if missing), installs dependencies with `uv sync`, runs your first pipeline on
dltHub, and prints next steps.

For a non-interactive setup with the recommended defaults:

```bash
mkdir my-workspace && cd my-workspace
uvx dlthub-start@latest --yes
uv run dlthub run load_sample_shop
uv run dlthub show
```

You can also pass a target directory (`uvx dlthub-start@latest my-workspace`),
but then the AI files live one level down — so launch your coding agent from
*inside* that directory. If the generated workspace needs `uv` and it is not
installed yet, the CLI offers to install it; or install it yourself via the
official [`uv` installation guide](https://docs.astral.sh/uv/getting-started/installation/).

## What You Get

- A Python dltHub workspace with project metadata customized to your directory name.
- A bundled scaffold copied from this package, not downloaded at create time.
- dltHub AI workbench files for your chosen coding agent (Claude, Cursor, or Codex).
- Shared dltHub AI toolkit files for data exploration, dltHub platform deployment, and REST API pipeline work.
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
| `--yes`, `-y` | Use the recommended path: the Claude workbench, install `uv` if missing, and run `uv sync`. |
| `--agent claude` | Use the Claude workbench files. Choose exactly one agent (`claude`, `cursor`, or `codex`); defaults to `claude`. |
| `--agent cursor` | Use the Cursor workbench files. |
| `--agent codex` | Use the Codex workbench files. |
| `--skip-uv-sync` | Create the scaffold and selected AI files, but stop before installing workspace dependencies. |
| `--verbose`, `-v` | Stream output from underlying subprocesses. |

Examples:

```bash
uvx dlthub-start@latest --yes                  # initialize in the current (empty) directory — recommended
uvx dlthub-start@latest --agent codex
uvx dlthub-start@latest --yes --skip-uv-sync
uvx dlthub-start@latest my-workspace --yes     # alternative: create + initialize a subdirectory
```

## Workspace contents

The bundled workspace is a quick, runnable first look: a sample online-shop
pipeline, local warehouse config, and a generated deployment module.

## Generated Workspace

The workspace is initialized at the project root, shaped roughly like this:

```text
.
|-- pyproject.toml
|-- pipeline.py
|-- __deployment__.py
|-- README.md
|-- .dlt/
|-- .mcp.json
`-- .claude/        # your selected agent (or .cursor/ / .codex/)
```

## Next Steps

From the workspace root:

```bash
uv run dlthub run load_sample_shop
uv run dlthub show
```

If you created the workspace with `--skip-uv-sync`, finish setup first with
`uv sync`. (If you scaffolded into a subdirectory, `cd` into it first.)

## Troubleshooting

`uvx: command not found`

Install the CLI with `pip install dlthub-start` (into your current Python
environment) and run `dlthub-start` instead. The CLI will still offer to
install `uv` before syncing the generated workspace dependencies.

`Directory not empty`

Run `dlthub-start` from an empty directory (hidden entries like `.git` and
`.gitignore` count), or pass a new target directory name. The CLI never writes
into a non-empty directory.

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
make publish
```

This removes any previous `dist/` artifacts, builds the package with
`uv build`, lists the artifacts, and prompts for a PyPI API token before
uploading with `uv publish`. Before publishing, run the release checklist in
[CONTRIBUTING.md](CONTRIBUTING.md) and make sure the version in
`pyproject.toml` has been bumped.
