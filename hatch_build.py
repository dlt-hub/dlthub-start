"""Bake the telemetry ingest key into the distribution at build time."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_KEY_MODULE = "src/create_dlthub_workspace/_telemetry_key.py"


class CustomBuildHook(BuildHookInterface):  # type: ignore[type-arg]
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        key = os.environ.get("DLTHUB_START_POSTHOG_KEY", "").strip()
        if not key:
            self.app.display_warning("DLTHUB_START_POSTHOG_KEY is not set; building with telemetry disabled.")
            return
        if not key.startswith("phc_"):
            raise ValueError("DLTHUB_START_POSTHOG_KEY must be a PostHog project key starting with 'phc_'.")
        self._module.write_text(f"POSTHOG_PROJECT_KEY = {key!r}\n", encoding="utf-8")
        build_data["artifacts"].append(_KEY_MODULE)

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        self._module.unlink(missing_ok=True)

    @property
    def _module(self) -> Path:
        return Path(self.root) / _KEY_MODULE
