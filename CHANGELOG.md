# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-06-02

### Changed
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
- Interactive project name prompt with default `my-workspace`, plus tests.
- Starter `prod` environment now defaults to MotherDuck: `.dlt/prod.secrets.toml` template, `motherduck` extra in `pyproject.toml`, and a "paste your MotherDuck token" step in the next-steps panel.
- Bundled toolkits expanded with `data-quality`, `dlthub-platform`, `filesystem-pipeline`, and `sql-database-pipeline`; regenerated AI workbench files reflect the new set.
- `CONTRIBUTING.md` notes the `git add -f` workaround for scaffold templates that match the shipped `.gitignore`.

### Changed
- Centralized user-facing strings into `strings.py`; refreshed onboarding and next-steps copy.
- Onboarding guidance now always recommends `dlthub-start@latest`.
- Bumped `WORKBENCH_REF` to `42ddb99` and refreshed the bundled AI workbench scaffold.
- `starter_transformations.py` now reads upstream data via `dlt.attach(...)` instead of importing `starter_pipe`, avoiding pipeline re-instantiation as an import side effect.

### Removed
- Stripped `uv.lock` from the bundled scaffold.
- `.dlt/access.config.toml` from the starter scaffold (notebooks share the `prod` env).
- Dead `[destination.warehouse]` block in `.dlt/config.toml` (per-env configs set their own destination).

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
