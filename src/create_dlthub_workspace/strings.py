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
PROMPT_PROJECT_NAME = "[bold]What should we call the workspace?[/bold]"
PROMPT_SCAFFOLD_HEADER = "\n[bold]Choose your onboarding experience[/bold] [dim](↑/↓ to move, enter to confirm)[/dim]"
PROMPT_AGENTS_HEADER = (
    "\n[bold]Choose AI workbench(es)[/bold] "
    "[dim](recommended: keep them all selected; space to toggle, enter to confirm)[/dim]"
)
PROMPT_INSTALL_UV = "uv is required but was not found. Install uv now?"
PROMPT_RUN_UV_SYNC = "Install workspace dependencies with `uv sync`?"


# Errors (call sites use .format() with named placeholders) -------------
ERROR_NO_AGENTS = "At least one AI workbench must be selected."
ERROR_UV_REQUIRED = "uv is required. Install uv and run this command again."
ERROR_UV_NOT_ON_PATH = "uv was installed, but it is not available on PATH yet. Open a new terminal and try again."
ERROR_UV_COMMAND_FAILED = "Command failed with exit code {returncode}: {cmd}"
ERROR_UV_COMMAND_NOT_FOUND = "Command not found: {cmd}"
ERROR_UV_INSTALLER_FETCH = "Could not download uv installer: {reason}"
ERROR_UV_NEEDS_POWERSHELL = "PowerShell is required to install uv on Windows."
ERROR_TARGET_NOT_EMPTY = "Target directory already exists and is not empty: {project_dir}"
ERROR_UNKNOWN_SCAFFOLD = "Unknown scaffold {scaffold!r}. Available: {available}"
ERROR_PARSE_PYPROJECT = "Could not parse generated pyproject.toml: {reason}"


# Status / info messages ------------------------------------------------
MSG_CANCELLED = "\n[yellow]Cancelled.[/yellow]"
MSG_ERROR_PREFIX = "[red]Error:[/red] {message}"
MSG_CREATING_WORKSPACE = "Creating workspace at {project_dir}"
MSG_CREATED = "[green]Created[/green] {project_dir}"
MSG_PACKAGE_NAME = "[dim]Project package name:[/dim] {package_name}"
MSG_SKIPPED_UV_AND_SYNC = "\n[yellow]Skipped[/yellow] uv install and dependency sync.\n"
MSG_SKIPPED_SYNC = "\n[yellow]Skipped[/yellow] dependency sync.\n"
MSG_INSTALLING_DEPS = "Installing dependencies"
MSG_INSTALLED_DEPS = "[green]Installed[/green] dependencies into .venv"


# Panel titles ----------------------------------------------------------
TITLE_BANNER = "dlthub-start v{version} [bold #C6D300](beta)[/bold #C6D300]"
TITLE_NEXT_STEPS_PANEL = "You're all set"
TITLE_RESUME_PANEL = "Almost there"


# Section labels inside panels ------------------------------------------
LABEL_CREATED = "Created"
LABEL_AI_WORKBENCHES = "AI workbenches:"
LABEL_WHAT_TO_TRY = "What to try next"
LABEL_FINISH_SETUP = "Finish setup"
LABEL_DOCS = "Docs:"


# Hint text / badges / taglines -----------------------------------------
HINT_RECOMMENDED_SUFFIX = " [dim](recommended)[/dim]"
HINT_NONE = "(none)"
HINT_BANNER_TAGLINE = "Onboarding"


# Links -----------------------------------------------------------------
LINK_DOCS_URL = "https://github.com/dlt-hub/dlthub-ai-workbench/blob/master/README.md"
LINK_DOCS_LABEL = "github.com/dlt-hub/dlthub-ai-workbench"


# Step labels (prose halves of the (label, command) tuples) -------------
STEPS_LABEL_CD = "Change into the workspace:"
STEPS_LABEL_ADD_MOTHERDUCK_CREDENTIALS = (
    "Add your MotherDuck database name and token to .dlt/prod.secrets.toml "
    "(open the file and follow the instructions inside)."
)
STEPS_LABEL_RUN_BREWERIES = "Run the ingestion pipeline in dltHub (you'll be prompted to connect/login):"
STEPS_LABEL_RUN_SAMPLE_SHOP = "Run the sample shop pipeline in dltHub (you'll be prompted to connect/login):"
STEPS_LABEL_VIEW_JOB_RUNS = "View runs for the brewery pipeline:"
STEPS_LABEL_VIEW_SAMPLE_SHOP_RUNS = "View runs for the sample shop pipeline:"
STEPS_LABEL_EDIT_PIPELINE = "Edit pipeline.py to swap in your own source, then re-run."
STEPS_LABEL_INSTALL_UV = "Install uv:"
STEPS_LABEL_INSTALL_DEPS = "Install workspace dependencies:"


# Commands shown to the user (the right halves of the tuples) -----------
CMD_INSTALL_UV_UNIX = "curl -LsSf https://astral.sh/uv/install.sh | sh"
CMD_UV_SYNC = "uv sync"
CMD_DLTHUB_RUN_BREWERIES = "uv run dlthub run load_breweries"
CMD_DLTHUB_RUN_LOAD_DATA = "uv run dlthub run load_data"
CMD_DLTHUB_JOB_RUNS_SHOW_BREWERIES = "uv run dlthub job runs show starter_pipeline.load_breweries"
CMD_DLTHUB_JOB_RUNS_SHOW_LOAD_DATA = "uv run dlthub job runs show pipeline.load_data"
CMD_CD = "cd {project_dir}"
