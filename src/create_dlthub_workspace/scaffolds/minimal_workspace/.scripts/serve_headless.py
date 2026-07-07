"""Serve one locally deployed interactive notebook headlessly (no browser).

`dlthub serve` deploys the local `__deployment__.py` manifest, picks an
interactive job, triggers it, waits until RUNNING, then opens the app URL in a
browser. This wrapper does two things differently:

1. Neutralizes the single browser-open (`_open_app_url`, the only open in the
   serve/launch flow) so nothing launches a browser.
2. Forces a specific job via the `--job-ref` slot. The local manifest has more
   than one interactive job (a default workspace dashboard is auto-added beside
   your notebook), so serve's positional selector alone is ambiguous and drops
   into an interactive picker. `narrow_candidates()` uses `job_ref` to pick the
   exact job deterministically — no prompt; errors if the ref isn't a candidate.

Pass the job's full manifest ref (namespaced under `jobs.`), e.g.
`jobs.onboarding_success` — NOT the `.py` path (a path is promoted to
`--deployment` and an undecorated notebook yields no job).

Usage (run from the workspace root so the run context resolves):
    uv run .scripts/serve_headless.py jobs.onboarding_success
"""

import sys

if len(sys.argv) < 2:
    sys.exit("usage: uv run .scripts/serve_headless.py <job-ref>   e.g. jobs.onboarding_success")
ref = sys.argv[1]

import dlt_runtime._runtime_command as rc

# The only browser-open in serve's flow (_runtime_command.py: _do_launch). serve
# is decorated with @requires_login/@requires_workspace, which inject
# auth_service + api_client, so calling it directly runs the full flow.
rc._open_app_url = lambda *args, **kwargs: None

# `interactive` selects all interactive jobs as candidates (regardless of
# trigger); `job_ref=ref` narrows to exactly this one without prompting.
rc.serve(selector_or_job_ref="interactive", job_ref=ref, follow=False)
