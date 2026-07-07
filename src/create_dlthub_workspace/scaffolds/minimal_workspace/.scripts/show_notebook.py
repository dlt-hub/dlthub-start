"""Open a deployed notebook's read-only "show" page in the dltHub web app.

Builds and opens:
    {APP_BASE}/w/{workspace_id}/notebooks/{job_ref}/show?hide_header=true

The workspace id is read from this workspace's `.dlt/config.toml` (so it tracks
whatever this workspace is connected to). Pass the job ref as the only argument.
The web-app base follows the workspace's pinned `runtime.api_base_url`
(api.* -> app.*, e.g. api.dlthub.test -> app.dlthub.test), defaulting to prod;
DLTHUB_APP_URL overrides both.

Usage (run from the workspace root):
    uv run .scripts/show_notebook.py jobs.onboarding_success
    DLTHUB_APP_URL=https://app.dlthub.test uv run .scripts/show_notebook.py jobs.onboarding_success
"""

import os
import sys
import tomllib
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

if len(sys.argv) < 2:
    sys.exit("usage: uv run .scripts/show_notebook.py <job-ref>   e.g. jobs.onboarding_success")
ref = sys.argv[1]


def _app_base(cfg: dict) -> str:
    env = os.environ.get("DLTHUB_APP_URL")
    if env:
        return env.rstrip("/")
    api = urlsplit(cfg.get("runtime", {}).get("api_base_url", ""))
    if api.hostname and api.hostname.startswith("api."):
        return f"{api.scheme or 'https'}://app.{api.hostname[4:]}"
    return "https://app.dlthub.com"


def _find_config() -> Path:
    """Locate .dlt/config.toml by walking up from this script (location-independent)."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".dlt" / "config.toml"
        if candidate.is_file():
            return candidate
    sys.exit("Could not find .dlt/config.toml above this script — run inside a workspace.")


cfg = tomllib.loads(_find_config().read_text())
ws = cfg.get("runtime", {}).get("workspace_id")
if not ws:
    sys.exit("No workspace_id in .dlt/config.toml — connect the workspace first.")

url = f"{_app_base(cfg)}/w/{ws}/notebooks/{ref}/show?hide_header=true"
print(f"Opening {url}")
webbrowser.open(url)
