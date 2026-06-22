.DEFAULT_GOAL := help

.PHONY: help dev test test-integration compile build clean-dist version-upgrade version-upgrade-patch version-upgrade-minor version-upgrade-major publish-library ci workspace workspace-env workspace-local workspace-stage workspace-dev workspace-here lint lint-fix format format-check fl lint-ci generate-ai update-ai check-ai lock-upgrade lock-check scaffold-lock-upgrade scaffold-lock-check scaffold-launcher-deps-check

PYTHONPYCACHEPREFIX ?= /tmp/create-dlthub-pyc
PACKAGE_MODULES := $(wildcard src/create_dlthub_workspace/*.py)
PYTHON_SOURCES := src tests tests_integration scripts

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

#
# Dev setup
#

dev: ## Install dev dependencies
	uv sync --extra dev

#
# Linting and formatting
#

lint: ## Lint with ruff and type-check with mypy
	uv run ruff check $(PYTHON_SOURCES)
	uv run mypy $(PYTHON_SOURCES)

lint-fix: ## Lint and autofix with ruff, type-check with mypy
	uv run ruff check --fix $(PYTHON_SOURCES)
	uv run mypy $(PYTHON_SOURCES)

format: ## Format with ruff
	uv run ruff format $(PYTHON_SOURCES)

format-check: ## Check formatting with ruff (no writes)
	uv run ruff format --check $(PYTHON_SOURCES)

fl: format lint-fix ## Format and lint-fix in one shot

lint-ci: format-check lint ## CI lint workflow (format-check then lint)

#
# Testing and build
#

test: ## Run unit tests (fast)
	uv run python -m unittest discover -s tests -t .

test-integration: ## Run e2e integration tests (slow; invokes real CLI + uv sync)
	uv run python -m unittest discover -s tests_integration -t .

compile: ## Byte-compile package and tests
	PYTHONPYCACHEPREFIX=$(PYTHONPYCACHEPREFIX) uv run python -m compileall $(PACKAGE_MODULES) tests

build: dev ## Build the package wheel
	uv build

clean-dist: ## Remove dist/ directory
	-@rm -r dist/

version-upgrade: ## Bump version in pyproject.toml + uv.lock. Prompts when interactive, else pass LEVEL=major|minor|patch (or use version-upgrade-{patch,minor,major})
	@level="$(LEVEL)"; \
	if [ -z "$$level" ]; then \
		if [ -t 0 ]; then \
			echo "Current version: $$(uv version --short)"; \
			printf "Bump which part? [major/minor/patch] "; \
			read level; \
		else \
			echo "error: no TTY for the prompt — pass LEVEL=major|minor|patch or run 'make version-upgrade-patch'"; exit 1; \
		fi; \
	fi; \
	case "$$level" in \
		major|minor|patch) ;; \
		*) echo "error: expected major, minor, or patch (got '$$level')"; exit 1;; \
	esac; \
	uv version --bump "$$level" --no-sync; \
	echo "version-upgrade: updated pyproject.toml and uv.lock — review 'git diff pyproject.toml uv.lock' and commit."

version-upgrade-patch: ## Bump the patch version non-interactively (AI/CI-friendly)
	@$(MAKE) version-upgrade LEVEL=patch

version-upgrade-minor: ## Bump the minor version non-interactively (AI/CI-friendly)
	@$(MAKE) version-upgrade LEVEL=minor

version-upgrade-major: ## Bump the major version non-interactively (AI/CI-friendly)
	@$(MAKE) version-upgrade LEVEL=major

publish: clean-dist build ## Build and publish dlthub-start to PyPI
	ls -l dist/
	@bash -c 'read -s -p "Enter PyPI API token: " PYPI_API_TOKEN; echo; \
	uv publish --token "$$PYPI_API_TOKEN"'

REMOVE_PREV_WORKSPACE ?= examples/my-workspace

workspace: ## Run dlthub-start at ./$(REMOVE_PREV_WORKSPACE) for a clean test workspace (pre-deletes existing)
	@case "$(REMOVE_PREV_WORKSPACE)" in *..*|"") echo "invalid REMOVE_PREV_WORKSPACE: $(REMOVE_PREV_WORKSPACE)"; exit 1;; esac
	rm -rf -- "$(REMOVE_PREV_WORKSPACE)"
	uv run dlthub-start "$(REMOVE_PREV_WORKSPACE)"

WORKSPACE_HERE_DIR ?= examples/here-workspace

API_BASE_URL ?= https://api.dlthub.test

workspace-env: ## Like workspace, but pointed at $(API_BASE_URL); persists the URL into the workspace config
	@case "$(REMOVE_PREV_WORKSPACE)" in *..*|"") echo "invalid REMOVE_PREV_WORKSPACE: $(REMOVE_PREV_WORKSPACE)"; exit 1;; esac
	rm -rf -- "$(REMOVE_PREV_WORKSPACE)"
	RUNTIME__API_BASE_URL=$(API_BASE_URL) DLT_RUNTIME_INSECURE=$(DLT_RUNTIME_INSECURE) uv run dlthub-start "$(REMOVE_PREV_WORKSPACE)"
	@awk -v url='$(API_BASE_URL)' '1; $$0 == "[runtime]" {print "api_base_url = \"" url "\""}' \
		"$(REMOVE_PREV_WORKSPACE)/.dlt/config.toml" > "$(REMOVE_PREV_WORKSPACE)/.dlt/config.toml.tmp"
	@mv "$(REMOVE_PREV_WORKSPACE)/.dlt/config.toml.tmp" "$(REMOVE_PREV_WORKSPACE)/.dlt/config.toml"
	@echo "workspace-env: pinned api_base_url = $(API_BASE_URL) in $(REMOVE_PREV_WORKSPACE)/.dlt/config.toml"

workspace-local: ## Scaffold a workspace pointed at the local runtime stack (api.dlthub.test); skips TLS verify (mkcert CA is not in Python's bundle)
	$(MAKE) workspace-env API_BASE_URL=https://api.dlthub.test DLT_RUNTIME_INSECURE=true

workspace-stage: ## Scaffold a workspace pointed at the staging stack (api.dlthub.net)
	$(MAKE) workspace-env API_BASE_URL=https://api.dlthub.net

workspace-dev: ## Scaffold a workspace pointed at the dev stack (api.dlthub.dev)
	$(MAKE) workspace-env API_BASE_URL=https://api.dlthub.dev

workspace-here: dev ## Init in place: make empty ./$(WORKSPACE_HERE_DIR), cd in, run the local CLI with no positional (pass ARGS="--yes --skip-uv-sync")
	@case "$(WORKSPACE_HERE_DIR)" in *..*|"") echo "invalid WORKSPACE_HERE_DIR: $(WORKSPACE_HERE_DIR)"; exit 1;; esac
	rm -rf -- "$(WORKSPACE_HERE_DIR)"
	mkdir -p -- "$(WORKSPACE_HERE_DIR)"
	cd "$(WORKSPACE_HERE_DIR)" && "$(CURDIR)/.venv/bin/dlthub-start" $(ARGS)

ci: compile lint-ci test test-integration lock-check scaffold-lock-check scaffold-launcher-deps-check check-ai build ## Run all CI checks locally

#
# Bundled AI workbench refresh
#

generate-ai: ## Refresh bundled AI workbench files in scaffolds (run after bumping WORKBENCH_REF)
	uv run python scripts/generate_ai.py

update-ai: ## Bump WORKBENCH_REF to latest workbench commit (or REF=<sha>) and regenerate scaffolds
	uv run python scripts/update_ai.py $(REF)

check-ai: ## CI guard: fail if generate-ai would produce a diff (generate-ai output is hidden unless it fails)
	@echo "check-ai: regenerating scaffolds (output hidden unless it fails)…"; \
	log="$$(mktemp)"; \
	if ! $(MAKE) --no-print-directory generate-ai >"$$log" 2>&1; then \
		echo "check-ai: generate-ai failed — its output:"; \
		cat "$$log"; rm -f "$$log"; exit 1; \
	fi; \
	rm -f "$$log"; \
	changed="$$(git status --porcelain -- src/create_dlthub_workspace/scaffolds)"; \
	if [ -z "$$changed" ]; then \
		echo "check-ai: OK — bundled scaffolds are up to date."; \
	else \
		echo "check-ai: FAILED — these scaffold files differ from 'make generate-ai' output; regenerate and commit them:"; \
		printf '%s\n' "$$changed" | sed 's/^/    /'; \
		echo ""; \
		git --no-pager diff -- src/create_dlthub_workspace/scaffolds; \
		exit 1; \
	fi

#
# Lockfiles
#

SCAFFOLD_DIR ?= src/create_dlthub_workspace/scaffolds/minimal_workspace

lock-upgrade: ## Upgrade the root uv.lock to the latest deps pyproject.toml allows (PKG=<name> to bump just one); review the diff and commit
	@echo "lock-upgrade: re-resolving uv.lock to the latest deps pyproject.toml allows…"
	uv lock $(if $(PKG),--upgrade-package $(PKG),--upgrade)
	@echo "lock-upgrade: done — review 'git diff uv.lock' and commit."

lock-check: ## CI guard: fail if the root uv.lock is out of sync with pyproject.toml
	@echo "lock-check: checking uv.lock against pyproject.toml…"; \
	log="$$(mktemp)"; \
	if uv lock --check >"$$log" 2>&1; then \
		rm -f "$$log"; \
		echo "lock-check: OK — uv.lock is in sync with pyproject.toml."; \
	else \
		echo "lock-check: FAILED — uv.lock is out of sync; run 'make lock-upgrade' and commit. uv output:"; \
		cat "$$log"; rm -f "$$log"; \
		exit 1; \
	fi

scaffold-lock-upgrade: ## Upgrade the bundled workspace uv.lock to the latest deps its pyproject allows (PKG=<name> to bump just one); review the diff and commit
	@echo "scaffold-lock-upgrade: re-resolving $(SCAFFOLD_DIR)/uv.lock to the latest deps its pyproject.toml allows…"
	uv lock $(if $(PKG),--upgrade-package $(PKG),--upgrade) --project $(SCAFFOLD_DIR)
	@echo "scaffold-lock-upgrade: done — review 'git diff $(SCAFFOLD_DIR)/uv.lock' and commit."

scaffold-lock-check: ## CI guard: fail if the bundled workspace uv.lock is out of sync with its pyproject
	@echo "scaffold-lock-check: checking $(SCAFFOLD_DIR)/uv.lock against its pyproject.toml…"; \
	log="$$(mktemp)"; \
	if uv lock --check --project $(SCAFFOLD_DIR) >"$$log" 2>&1; then \
		rm -f "$$log"; \
		echo "scaffold-lock-check: OK — uv.lock is in sync with pyproject.toml."; \
	else \
		echo "scaffold-lock-check: FAILED — uv.lock is out of sync; run 'make scaffold-lock-upgrade' and commit. uv output:"; \
		cat "$$log"; rm -f "$$log"; \
		exit 1; \
	fi

scaffold-launcher-deps-check: ## CI guard: minimal_workspace pyproject.toml covers Batch/Marimo/Dashboard launcher deps
	uv sync --frozen --project $(SCAFFOLD_DIR)
	uv run --project $(SCAFFOLD_DIR) python scripts/check_scaffold_launcher_deps.py $(SCAFFOLD_DIR)
