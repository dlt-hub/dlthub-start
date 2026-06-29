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

The CLI scaffolds the workspace, checks for `uv` (offering to install it if
missing), installs dependencies with `uv sync`, logs you in to dltHub and
connects a `playground` workspace, then prompts for your coding agent and sets
up its files. Finally it asks whether to launch that agent in the workspace —
seeded with a prompt to deploy and run the sample pipeline, so the agent (not
the CLI) runs it. Decline, or use an agent with no command-line launcher, and it
prints that prompt (with the bundled skill's location) and copies it to your
clipboard so you can paste it into an agent you start yourself.

The full setup runs through the interactive prompts:

```bash
mkdir my-workspace && cd my-workspace
uvx dlthub-start@latest
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
- A zero-setup `playground` destination, managed by the dltHub platform — no credentials or config.

## Usage

```bash
uvx dlthub-start@latest [project-dir] [options]
```

Initializes a workspace **in place** when the target is empty: the current
directory by default, or `project-dir` if given. A non-empty target never
fails — the CLI scaffolds into a free directory instead and tells you where it
landed. With no argument it nests a `playground` subdirectory (then
`playground-1`, `playground-2`, …); an explicit `project-dir` that's occupied
falls back to `<project-dir>-1`, `<project-dir>-2`, …. Existing contents are
left untouched. A directory holding only benign cruft — editor/OS files
(`.idea`, `.vscode`, `.DS_Store`), tool caches, and a bare `.git` — still counts
as empty and initializes in place; anything the scaffold ships (`.gitignore`,
`.dlt`, …) counts as content and triggers the fallback.

Common options:

| Option | Description |
| --- | --- |
| `--agent claude` | Use the Claude workbench files. Choose exactly one agent (`claude`, `cursor`, or `codex`); if omitted you're prompted (defaults to `claude`). |
| `--agent cursor` | Use the Cursor workbench files. |
| `--agent codex` | Use the Codex workbench files. |
| `--verbose`, `-v` | Stream output from underlying subprocesses. |

Examples:

```bash
uvx dlthub-start@latest                         # interactive setup in the current (empty) directory — recommended
uvx dlthub-start@latest --agent codex           # skip the agent prompt
uvx dlthub-start@latest my-workspace            # alternative: create + initialize a subdirectory
```

## Workspace contents

The bundled workspace is a quick, runnable first look: a sample online-shop
pipeline, an interactive onboarding notebook, and a generated deployment module.

## Generated Workspace

The workspace is initialized at the project root, shaped roughly like this:

```text
.
|-- pyproject.toml
|-- pipeline.py
|-- __deployment__.py
|-- notebooks/
|-- README.md
|-- .dlt/
|-- .mcp.json
`-- .claude/        # your selected agent (.cursor/, or .agents/ for codex)
```

## Next Steps

From the workspace root:

```bash
uv run dlthub run load_sample_shop
uv run dlthub show
```

(If you scaffolded into a subdirectory, `cd` into it first.)

## Troubleshooting

`uvx: command not found`

Install the CLI with `pip install dlthub-start` (into your current Python
environment) and run `dlthub-start` instead. The CLI will still offer to
install `uv` before syncing the generated workspace dependencies.

`My workspace landed in a `playground`/`-1` subdirectory`

That's expected when the target wasn't empty: rather than refuse, the CLI
scaffolds into a free directory and prints where it went. To control the
location, pass an explicit empty target — `uvx dlthub-start@latest my-workspace`
— or run from an empty directory. The CLI never writes into a non-empty
directory; it picks a fresh one alongside it.

`uv sync` fails

Re-run with `--verbose` to see subprocess output:

```bash
uvx dlthub-start@latest my-workspace --verbose
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
