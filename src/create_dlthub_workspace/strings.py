"""User-facing CLI copy. Single source of truth for everything the user reads
in the terminal.

Naming convention:
  PROMPT_*  : interactive prompt text (headers + questions)
  ERROR_*   : exception messages — use ``.format()`` with named placeholders
  MSG_*     : status / info lines printed during execution
  LABEL_*   : section labels inside panels
  TITLE_*   : panel titles
  HINT_*    : ancillary text (badges, placeholders, taglines)
  LINK_*    : URLs + their display labels
  STEPS_*   : prose labels for ordered command lists
  CMD_*     : shell command snippets shown to the user

Rich markup stays in the strings — the styling IS the presentation. argparse
``help=`` text intentionally stays in ``cli.py`` since it's tightly bound to
the argument definitions and needs default-value interpolation.
"""

from __future__ import annotations


# Prompts ---------------------------------------------------------------
PROMPT_AGENT_HEADER = (
    "\n[bold]2. Claude/Cursor/Codex-native dlt pipeline building with dltHub platform[/bold]"
    "\nNow create your own dlt pipeline to load data from a REST API source into the dltHub platform."
    "\n\n[bold]Which coding agent do you want to use?[/bold] [dim](↑/↓ to move, enter to confirm)[/dim]"
)
PROMPT_INSTALL_UV = "uv is required but was not found. Install uv now?"


# Errors (call sites use .format() with named placeholders) -------------
ERROR_UNKNOWN_AGENT = "Unknown agent {agent!r} for scaffold {scaffold!r}. Available: {available}"
ERROR_UV_REQUIRED = "uv is required. Install uv and run this command again."
ERROR_UV_NOT_ON_PATH = "uv was installed, but it is not available on PATH yet. Open a new terminal and try again."
ERROR_UV_COMMAND_FAILED = "Command failed with exit code {returncode}: {cmd}"
ERROR_UV_COMMAND_NOT_FOUND = "Command not found: {cmd}"
ERROR_UV_INSTALLER_FETCH = "Could not download uv installer: {reason}"
ERROR_UV_NEEDS_POWERSHELL = "PowerShell is required to install uv on Windows."
ERROR_UNKNOWN_SCAFFOLD = "Unknown scaffold {scaffold!r}. Available: {available}"
ERROR_PARSE_PYPROJECT = "Could not parse generated pyproject.toml: {reason}"
ERROR_WRITE_FAILED = "Couldn't write to {path}: {reason}"
ERROR_READ_FAILED = "Couldn't read {path}: {reason}"


# Status / info messages ------------------------------------------------
# Out-of-band stderr note shown when a hidden dev flag (--setup-only / --scaffold-only) is used.
MSG_TESTING_SHORTCUT_NOTE = (
    "[yellow]Note:[/yellow] --setup-only / --scaffold-only are non-interactive shortcuts for testing/CI. "
    "They cut the guided setup short, so onboarding is incomplete. "
    "Run without them for the full interactive setup."
)
MSG_CANCELLED = "\n[yellow]Cancelled.[/yellow]"
MSG_ERROR_PREFIX = "[red]Error:[/red] {message}"
MSG_UNEXPECTED_ERROR = "[red]Unexpected error:[/red] {message}"
MSG_UNEXPECTED_ERROR_HINT = "[dim]Re-run with --verbose to see the full traceback.[/dim]"
MSG_RELOCATED = "[yellow]Heads up:[/yellow] {relocated_from} isn't empty — scaffolding into {project_dir} instead."
MSG_CREATING_WORKSPACE = "Creating workspace at {project_dir}"
MSG_CREATED = "Created {project_dir}"
MSG_PACKAGE_NAME = "Project package name: {package_name}"
MSG_SKIPPED_UV_AND_SYNC = "\n[yellow]Skipped[/yellow] uv install and dependency sync.\n"
MSG_SKIPPED_SYNC = "\n[yellow]Skipped[/yellow] dependency sync.\n"
MSG_INSTALLING_DEPS = "Installing dependencies"
MSG_INSTALLED_DEPS = "Installed dependencies into .venv"
MSG_ADDING_AGENT_FILES = "Adding {agent} workbench files"
MSG_ADDED_AGENT_FILES = "Added {agent} workbench files"
MSG_LAUNCHING_AGENT = (
    "\n[bold #59C1D5]Launching {agent}[/bold #59C1D5] in your workspace — your skills and MCP server are ready.\n"
)
# First-run flow: each sub-step has a running (spinner/active) line and a "done" line it ticks to.
MSG_LOGGING_IN = "Logging in to dltHub — follow the prompts below"
MSG_LOGGED_IN = "Logged in to dltHub"
MSG_CONNECTING_PLAYGROUND = "Connecting to a {workspace} workspace"
MSG_CONNECTED_PLAYGROUND = "Connected to the {workspace} workspace"
MSG_RUNNING_FIRST_PIPELINE = "Running your first pipeline"
MSG_RAN_FIRST_PIPELINE = "Ran your first pipeline"
MSG_SHOWING_RUN = "Showing your pipeline run and its logs"
MSG_SHOWED_RUN = "Showed your pipeline run"
# "What just happened" summary, shown after the first run and before the agent picker.
MSG_PLAYGROUND_READY = (
    "\n[bold]1. The dltHub platform playground experience is set[/bold]"
    "\nWe created a demo dlt pipeline and set up your dltHub playground."
)
MSG_FIRST_RUN_FAILED = (
    "\n[yellow]Heads up:[/yellow] couldn't finish the first pipeline run ({message}). "
    "Your workspace is set up — run it yourself with the steps below."
)


# Panel titles ----------------------------------------------------------
TITLE_BANNER = "dlthub-start v{version} [bold #C6D300](beta)[/bold #C6D300]"
TITLE_NEXT_STEPS_PANEL = "You're all set"
TITLE_RESUME_PANEL = "Almost there"
TITLE_DIR_NOT_EMPTY = "Directory not empty"

# Shown on the next-steps / resume panels only when scaffolding into a
# subdirectory (the AI files are nested one level down).
MSG_AGENT_WORKSPACE_NOTE = (
    "Note for AI agents: the AI skills and MCP server are inside this workspace — "
    "run your session from the workspace root (the new directory), not the parent, "
    "so they're in scope."
)


# Directory-not-empty response (rendered as a panel, not a raw error) ----
MSG_DIR_NOT_EMPTY = (
    "Can't initialize a dltHub workspace here — this directory isn't empty:\n\n"
    "  [bold]{project_dir}[/bold]\n\n"
    "The directory must be empty apart from editor/OS cruft and a bare .git — "
    "entries like .gitignore, .dlt, and .venv count as content.\n\n"
    "Start from an empty directory, or create a new one:\n\n"
    "  [bold #59C1D5]uvx dlthub-start@latest my-workspace[/bold #59C1D5]\n\n"
    "[dim]Note for AI agents: initializing a workspace installs AI skills and an "
    "MCP server into the target directory. Run it from that directory and keep "
    "your session there (the workspace root) so they're in scope.[/dim]"
)


# Section labels inside panels ------------------------------------------
LABEL_WHAT_TO_TRY = "What to try next"
LABEL_FINISH_SETUP = "Finish setup"
LABEL_DOCS = "Docs:"


# Links (URL + its display label) ---------------------------------------
LINK_DOCS_URL = "https://github.com/dlt-hub/dlthub-ai-workbench/blob/master/README.md"
LINK_DOCS_LABEL = "github.com/dlt-hub/dlthub-ai-workbench"


# Hint text / badges / taglines -----------------------------------------
HINT_RECOMMENDED_SUFFIX = " [dim](recommended)[/dim]"
HINT_CODEX_SUFFIX = " [dim](or other agents, e.g. Copilot)[/dim]"
HINT_NONE = "(none)"
HINT_BANNER_TAGLINE = "Onboarding"


# Step labels (prose halves of the (label, command) tuples) -------------
STEPS_LABEL_CD = "Change into the workspace:"
STEPS_LABEL_RUN_SAMPLE_SHOP = "Run the sample shop pipeline in dltHub (you'll be prompted to connect/login):"
STEPS_LABEL_VIEW_SAMPLE_SHOP_RUNS = "View runs for the sample shop pipeline:"
STEPS_LABEL_EDIT_PIPELINE = "Edit pipeline.py to swap in your own source, then re-run."
STEPS_LABEL_BUILD_OWN_SOURCE = (
    "Tell your agent to navigate to the directory you just ran the dlthub-start command in and paste this prompt:"
)
HINT_PROMPT_COPIED = "✓ Already copied to your clipboard — just paste it in."
STEPS_LABEL_INSTALL_UV = "Install uv:"
STEPS_LABEL_INSTALL_DEPS = "Install workspace dependencies:"


# Commands shown to the user (the right halves of the tuples) -----------
CMD_INSTALL_UV_UNIX = "curl -LsSf https://astral.sh/uv/install.sh | sh"
CMD_UV_SYNC = "uv sync"
CMD_DLTHUB_RUN_SAMPLE_SHOP = "uv run dlthub run load_sample_shop"
CMD_DLTHUB_JOB_RUNS_SHOW_SAMPLE_SHOP = "uv run dlthub job runs show pipeline.load_sample_shop"
CMD_CD = "cd {project_dir}"
CMD_BUILD_OWN_SOURCE_PROMPT = (
    "Load the 50 most recent GitHub issues from https://github.com/dlt-hub/dlt "
    "and show me the data on the dltHub query editor"
)
