"""Open a deployed notebook's read-only "show" page in the dltHub web app.

Builds and opens:
    {web_ui_base}/w/{workspace_id}/notebooks/{job_ref}/show?hide_header=true

The workspace id and web-app base come from the active workspace context —
`dlt_runtime.urls` mirrors the web app's routes — so the URL tracks whatever
stack this workspace is connected to. Pass the job ref as the only argument.

Usage (run from the workspace root so the workspace context resolves):
    uv run .scripts/show_notebook.py jobs.onboarding_success
"""

import sys
import webbrowser

if len(sys.argv) < 2:
    sys.exit("usage: uv run .scripts/show_notebook.py <job-ref>   e.g. jobs.onboarding_success")
ref = sys.argv[1]

from dlt._workspace._workspace_context import active
from dlt._workspace.exceptions import WorkspaceRunContextNotAvailable
from dlt_runtime.urls import workspace_url

try:
    ws = active().runtime_config.workspace_id
except WorkspaceRunContextNotAvailable:
    sys.exit("No workspace found here — run from the workspace root.")
if not ws:
    sys.exit("No workspace_id in .dlt/config.toml — connect the workspace first.")

url = f"{workspace_url(ws)}/notebooks/{ref}/show?hide_header=true"
print(f"Opening {url}")
webbrowser.open(url)
