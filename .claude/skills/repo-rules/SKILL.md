---
name: repo-rules
description: Project-wide rules for the dlthub-start repo. ALWAYS read before modifying any file in this codebase.
---

# Repo rules

Read these before editing anything in this repo.

## 1. Never hand-edit generated AI workbench files

The vendored AI workbench files under
`src/create_dlthub_workspace/scaffolds/minimal_workspace/_agents/**` (Claude,
Cursor, and Codex) are **auto-generated** by `make generate-ai` (and
`make update-ai`) from the pinned `WORKBENCH_REF`. Never edit them directly —
`make check-ai` will fail on the drift, and your change is overwritten on the
next regeneration.

To change that content, edit the upstream `dlt-hub/dlthub-ai-workbench` source,
then bump/regenerate here via `make update-ai` (or `make generate-ai` against
the already-pinned ref) and commit the regenerated scaffold.
