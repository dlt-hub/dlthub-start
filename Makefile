.DEFAULT_GOAL := help

.PHONY: help dev test test-integration compile build clean-dist publish-library ci workspace lint lint-fix format format-check fl lint-ci generate-ai update-ai check-ai

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

publish: clean-dist build ## Build and publish dlthub-start to PyPI
	ls -l dist/
	@bash -c 'read -s -p "Enter PyPI API token: " PYPI_API_TOKEN; echo; \
	uv publish --token "$$PYPI_API_TOKEN"'

REMOVE_PREV_WORKSPACE ?= examples/my-workspace

workspace: ## Run dlthub-start at ./$(REMOVE_PREV_WORKSPACE) for a clean test workspace (pre-deletes existing)
	@case "$(REMOVE_PREV_WORKSPACE)" in *..*|"") echo "invalid REMOVE_PREV_WORKSPACE: $(REMOVE_PREV_WORKSPACE)"; exit 1;; esac
	rm -rf -- "$(REMOVE_PREV_WORKSPACE)"
	uv run dlthub-start "$(REMOVE_PREV_WORKSPACE)"

ci: compile lint-ci test test-integration check-ai build ## Run all CI checks locally

#
# Bundled AI workbench refresh
#

generate-ai: ## Refresh bundled AI workbench files in scaffolds (run after bumping WORKBENCH_REF)
	uv run python scripts/generate_ai.py

update-ai: ## Bump WORKBENCH_REF to latest workbench commit (or REF=<sha>) and regenerate scaffolds
	uv run python scripts/update_ai.py $(REF)

check-ai: ## CI guard: fail if generate-ai would produce a diff
	$(MAKE) generate-ai
	git diff --exit-code -- src/create_dlthub_workspace/scaffolds
