# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `make scaffold-lock-upgrade` re-resolves the bundled workspace's `uv.lock` to the newest dependency versions its `pyproject.toml` allows (`PKG=<name>` to bump a single package), with a companion `make scaffold-lock-check` drift guard. Matching `make lock-upgrade` / `make lock-check` targets do the same for the root `uv.lock`; both checks run in CI and are included in `make ci`.

### Changed
- Bundled AI toolkits are now `one-shot` and `data-exploration` (previously `one-shot-pipeline` and `dlthub-platform`). The one-shot toolkit is reshaped around `create-minimal-pipeline` and `deploy-minimal-pipeline`; the platform deployment toolkit (`deploy-workspace`, `prepare-deployment`, `setup-runtime`, `debug-deployment`, …) is dropped in favor of `data-exploration` (`explore-data`, `build-notebook`).
- Bumped `WORKBENCH_REF` to `eeacfb8a` and refreshed the bundled AI workbench scaffolds across all agents (claude/codex/cursor).
- Widened the startup banner logo so it no longer renders compressed, and added a blank line above it for spacing.
- The minimal workspace now loads into the managed, zero-config `playground` delta destination instead of local `warehouse` (duckdb), so data persists across ephemeral job runs. Bumps the `dlt` floor to `[hub,deltalake]>=1.27.2` (drops the unused `filesystem` extra, adds `deltalake` which pulls `deltalake`/`pyarrow`; `1.28.0` in `uv.lock`) and drops the orphaned `[destination.warehouse]` block.

## [0.7.0] - 2026-06-12

### Changed
- The coding-agent prompt now comes at the *end* of setup — after your first pipeline run — and the agent's AI workbench files are laid down as the final step, so you see the pipeline work before picking your editor. Passing `--agent` still skips the prompt. (Internally, the two-phase plan/execute split was collapsed into a single linear flow.)
- A non-empty target no longer stops with a "Directory not empty" error. Instead `dlthub-start` scaffolds into a free directory and tells you where it landed: with no argument it initializes in the current directory when empty, otherwise into a `playground` subdirectory (`playground-1`, `playground-2`, … if that's taken too); an explicit name that's occupied falls back to `<name>-1`, `<name>-2`, …. The original directory's contents are never touched. (The `WorkspaceDirectoryNotEmptyError` / exit-code-`2` path remains only as a defensive guard against races.)
- A directory that holds only benign cruft — editor/OS files (`.idea`, `.vscode`, `.DS_Store`, `Thumbs.db`), tool caches (`__pycache__`, `.ruff_cache`, `.mypy_cache`, `.pytest_cache`), and a bare `.git` — now counts as empty, so a freshly `git init`'d or IDE-touched directory still initializes in place instead of falling back. Anything the scaffold itself ships (e.g. `.gitignore`, `.dlt`) still counts as content, so the user's copy is never clobbered.
- The first pipeline run now streams its `--follow` logs live instead of hiding them behind a spinner. The step flags a "streaming live logs" note, then prints the run's output line by line — recolored uniformly (dim cyan) so it reads as nested, live output. A spinner and streamed output can't share the terminal (Rich's live spinner fights the child for the cursor), so the spinner is dropped for this step; the run always streams regardless of `--verbose`.
- `--yes`/`-y` and `--skip-uv-sync` are now hidden, non-interactive shortcuts for tests/CI only — both are removed from `--help` and print a stderr notice when used, because they cut the guided setup short (`--yes` skips the prompts and the first run; `--skip-uv-sync` also skips dependency sync), leaving the workspace scaffolded but never run. The interactive flow (no flag) is now the only documented path. The flags still work when explicitly passed, so nothing breaks for automated callers.
- Bumped `dlthub-client` from `0.27.6` to `0.27.7` in the minimal workspace's `uv.lock`.
- The post-setup panel is trimmed to the hand-off: after the first run it shows the prompt to give your agent (with a "copied to your clipboard" confirmation) and a link to the docs — nothing else. The "Created" file tree now prints during scaffolding (right under `Created <dir>`) instead of in the final panel. The bundled workspace `README.md` is now a few lines so it doesn't compete with the guided flow.
- The agent picker labels `codex` as `codex (or other agents, e.g. Copilot)` since its `.agents/` layout is a cross-agent convention.
- Improved the styling and wording of the guided setup output to make the flow clearer.
- Hardened error handling: unexpected failures now print a one-line message (full traceback only with `--verbose`) instead of a raw stack trace; filesystem problems while creating the workspace report `Couldn't read/write <path>`; and best-effort steps degrade gracefully — a failed first pipeline run, an agent with no terminal launcher, or a clipboard miss now warn and continue instead of aborting setup. (Known gap: a remote run that fails but exits 0 still reports success — tracked for a follow-up.)

### Added
- After laying down its workbench files, `dlthub-start` now launches your chosen coding agent right in the workspace — seeded with the starter prompt `Build a dlt pipeline for the [API name] API and load [endpoint/data] into DuckDB.` — so you land in a session with the skills and MCP server already in scope. Claude and Codex launch via their CLIs (`claude` / `codex`); an agent with no terminal launcher (e.g. the Cursor app) falls back to printing that prompt and copying it to your clipboard. Skipped under `--yes`, since the launch is interactive.
- The minimal workspace now ships a committed `uv.lock`, so `uv sync` installs from pinned versions instead of resolving against the PyPI index on every workspace creation — faster, reproducible, and resilient to intermittent `pypi.org/simple/` outages. Renaming a generated workspace rewrites the root package name in `uv.lock` in lock-step with `pyproject.toml`, so the two never diverge — otherwise uv would treat the bundled lock as out of date and fall back to a full re-resolution against `pypi.org/simple/`, defeating the purpose of shipping the lock.

## [0.6.0] - 2026-06-10

### Added
- After setup, `dlthub-start` automatically runs your first pipeline on dltHub: it logs in, binds the project to a `playground` workspace (creating it only if it doesn't already exist), runs `load_sample_shop` with `--follow` (waiting for the run to finish), and opens the workspace overview with `dlthub show`. The post-run next-steps panel then shows a ready-to-paste prompt addressed to your chosen coding agent (`claude`/`cursor`/`codex`) for building a pipeline against your own source — and copies it to your clipboard so it's one paste away. Skipped under `--yes`, since the login is interactive.

### Changed
- `uv sync` and the first pipeline run now happen automatically instead of being prompted. `--skip-uv-sync` still opts out of dependency sync (and, with it, the first run).
- `dlthub-start` now initializes a workspace **in place** — the current directory by default (the workspace-name prompt is gone). An explicit positional argument still targets a named subdirectory. Either way the target must be empty; a non-empty target stops with a dedicated "Directory not empty" message and exit code `2` instead of a generic error. Next-steps guidance adapts: the `cd` step is omitted when initializing in place, and a note reminds AI agents to run from the workspace root when a subdirectory is used.
- Bundled AI toolkits are now `one-shot-pipeline` and `dlthub-platform` (previously `data-exploration`, `dlthub-platform`, and `rest-api-pipeline`).
- The minimal workspace now also depends on `pyarrow` and `ibis-framework[duckdb]` for local data access.
- Bumped `WORKBENCH_REF` to `21b9bba4` and refreshed the bundled AI workbench scaffolds.
- `make check-ai` is clearer: it confirms when the bundled scaffolds are up to date, lists exactly which files differ (including untracked additions) when they're not, and hides the noisy `generate-ai` output unless it fails.

### Removed
- Removed the `starter_workspace` scaffold along with the `--scaffold` flag and the interactive scaffold picker. `minimal_workspace` is now the only bundled scaffold.
- The minimal workspace no longer ships `report_notebook.py`. On dltHub Platform the notebook had to re-run the whole pipeline to repopulate the worker-local DuckDB before charting, which made it slow and undercut the first-run experience. It's removed temporarily until shared workspace storage lands and the notebook speed issue is fixed; agents can still build notebooks on demand via the `data-exploration` toolkit.

### Fixed
- `python -m create_dlthub_workspace` now propagates the CLI exit code (it previously always exited `0` because `__main__` ignored `main()`'s return value).

## [0.5.3] - 2026-06-04

### Added
- `make update-ai` (`scripts/update_ai.py`): bumps `WORKBENCH_REF` to the latest workbench commit (or `REF=<sha>`) and regenerates all scaffolds in one step.

### Changed
- Bumped `WORKBENCH_REF` to `34b410d0` and refreshed the bundled AI workbench scaffolds.
- Documented `make update-ai` in CONTRIBUTING.md and fixed README's stale multi-select `--agent` wording to reflect single-agent selection.

## [0.5.2] - 2026-06-02

### Added
- `make publish` (and `make clean-dist`) target to build and publish `dlthub-start` to PyPI, with accompanying README and CONTRIBUTING docs.

### Changed
- Agent selection is now single-select: you choose exactly one coding agent (claude, cursor, or codex) instead of several. `--agent` takes a single value and `--yes` uses the recommended `claude`. AI files are vendored per-agent under `_agents/<agent>/` (each with its own `.dlt/.toolkits`), and only the selected agent's files are written to the new workspace — fixing the bug where one selection still shipped the other agents' toolkits (notably codex's `.agents/`). `generate_ai.py` now generates each agent in isolation.
- The minimal workspace is now a complete, runnable "Hello World" example: `pipeline.py` ingests a public sample online-shop REST API (`sample_shop`), a new `report_notebook.py` (Marimo) charts the loaded data, and a new `README.md` walks through the ingest → load → visualise → deploy loop. Next-steps copy and the "Created" panel updated accordingly; `pyproject.toml` gains `marimo` and `altair`.
- The recommended default scaffold is now `minimal_workspace`: `--yes` and the interactive picker default to the minimal single-pipeline workspace, which is also listed first in the scaffold options.
- Bumped `WORKBENCH_REF` to `c4250057` and refreshed the bundled AI workbench scaffold.
- Polished the Hello World onboarding: the minimal scaffold's picker label is now "Hello World", the agent-selection prompt reads "Choose your coding agents", and the post-setup "next steps" show a relative `cd` path.
- Renamed the minimal workspace's sample job `load_data` → `load_sample_shop` and dropped its `expose` display name (so the dltHub UI shows a single, clear job name).
- The minimal workspace now depends on `dlt[hub,filesystem]`.

### Removed
- Dropped the `data-quality` and `transformations` toolkits from the bundled scaffolds (removing the related skills, including ontology/CDM modeling).
- Dropped the `sql-database-pipeline` and `filesystem-pipeline` toolkits from the bundled scaffolds, leaving `data-exploration`, `dlthub-platform`, and `rest-api-pipeline`.

## [0.4.0] - 2026-05-26

### Added
- Per-tool AI skills now ship in scaffolds: full `SKILL.md` (and reference) trees under `.claude/skills/` and `.cursor/skills/` for both `starter_workspace` and `minimal_workspace`, exposing toolkit workflows (e.g. `rest-api-pipeline-workflow`, `data-quality-workflow`, `dlthub-platform-workflow`, `transformations-workflow`) and per-step skills (`create-*`, `add-*`, `adjust-*`, `debug-*`, `deploy-*`, `explore-data`, `build-notebook`, `init-dlthub-workspace`, ...) directly to Claude Code and Cursor. `scripts/generate_ai.py` was extended to materialize them.
- CI `lock-check` job that runs `uv lock --check` to fail PRs when `uv.lock` drifts from `pyproject.toml`.

### Changed
- Refreshed onboarding guidance for `dlt show run` and MotherDuck credentials.

### Fixed
- MotherDuck credentials handling in scaffolded workspaces.

## [0.3.0] - 2026-05-21

### Added
- Starter `prod` environment now defaults to MotherDuck: `.dlt/prod.secrets.toml` template, `motherduck` extra in `pyproject.toml`, and a "paste your MotherDuck token" step in the next-steps panel.
- Bundled toolkits expanded with `data-quality`, `dlthub-platform`, `filesystem-pipeline`, and `sql-database-pipeline`; regenerated AI workbench files reflect the new set.
- `CONTRIBUTING.md` notes the `git add -f` workaround for scaffold templates that match the shipped `.gitignore`.

### Changed
- Bumped `WORKBENCH_REF` to `42ddb99` and refreshed the bundled AI workbench scaffold.
- `starter_transformations.py` now reads upstream data via `dlt.attach(...)` instead of importing `starter_pipe`, avoiding pipeline re-instantiation as an import side effect.

### Removed
- `.dlt/access.config.toml` from the starter scaffold (notebooks share the `prod` env).
- Dead `[destination.warehouse]` block in `.dlt/config.toml` (per-env configs set their own destination).

## [0.2.1] - 2026-05-19

### Added
- Interactive project name prompt with default `my-workspace`, plus tests.

### Changed
- Centralized user-facing strings into `strings.py`; refreshed onboarding and next-steps copy.
- Onboarding guidance now always recommends `dlthub-start@latest`.

### Removed
- Stripped `uv.lock` from the bundled scaffold.

### Fixed
- MCP dependency error in scaffolds.

## [0.2.0] - 2026-05-19

### Added
- Beta classifier on the package.
- MCP dependencies.
- AI integration via `generate-ai` / `check-ai` subcommands (replacing direct `ai` invocation), `--overwrite` flag, and default agents set to "all".
- Unit, integration, and cross-platform e2e tests; CI updated for cross-platform runs; `.codexignore` files.
- File-tree printing with a sync test.
- Company LICENSE.
- `lint` / `format` Make targets and dependencies.
- Prompts to install `uv` and run `uv sync`.
- Scaffolds: `starterpack`, `minimal_workspace`, plus `.gitignore` for `starter-workspace`.
- Selection output, recommendations, and explicit `.venv` mention in toolkit display.
- Make target for test-workspace handling.

### Changed
- **Package renamed** `create-dlthub-workspace` → `dlthub-start` (CLI entrypoint and `pyproject.toml`).
- Default destination for `start_workspace` switched from MotherDuck to DuckDB; stray scaffold removed.
- CLI usage renamed `dlt` → `dlthub`.
- Bumped `dlt[hub]` version in scaffolds.
- Workbench pinned to a specific commit; Windows encoding issue fixed.
- Next-steps copy aligned with scaffolds; `cd` moved to step 1.
- Source switched from `github_api` to a public no-auth API; API limit handling adjusted.
- Plan and execute phases split.
- Stdout/stderr from subprocesses suppressed.
- License pointer updated.
- Lint/format conformed to runtime repo.
- Notebook refactored and moved to `notebooks/` dir; `starter_report` removed.
- `make compile` no longer recurses into bundled scaffolds / generated `.venv`.

### Fixed
- Windows test string issue.
- `dlthub toolkit install` CLI command order.

## [0.1.0] - 2026-05-13

### Added
- Initial scaffold of the `create-dlthub-workspace` CLI.
- Makefile and GitHub Actions setup.
- Recursive `.dlt` files.
