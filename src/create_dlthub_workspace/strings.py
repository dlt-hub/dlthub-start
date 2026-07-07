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

Rich markup stays in strings that are printed as markup. Strings rendered
through the ``Text``-based display helpers (error blocks, launch plan, agent
hand-off) stay plain here and are styled in ``display.py`` — markup added to
them would print literally. argparse ``help=`` text intentionally stays in
``cli.py`` since it's tightly bound to the argument definitions and needs
default-value interpolation.
"""

from __future__ import annotations

from . import config


# Prompts ---------------------------------------------------------------
PROMPT_AGENT_HEADER = (
    "\n[bold]Claude/Cursor/Codex-native dlt pipeline building with dltHub platform[/bold]"
    "\n{lead}"
    "\n\n[bold]Which coding agent do you want to use?[/bold] [dim](↑/↓ to move, enter to confirm)[/dim]"
)
PROMPT_AGENT_LEAD_SETUP = "Set up your coding agent — it takes over from here."
PROMPT_INSTALL_UV = "uv is required but was not found. Install uv now?"
PROMPT_LAUNCH_AGENT = "How do you want to continue?"
PROMPT_LAUNCH_YES = "Launch {agent} now and hand it this prompt"
PROMPT_LAUNCH_NO = "Skip — I'll paste the prompt into an agent myself"
# Shown before the launch confirmation so the user sees where it runs and the exact prompt.
MSG_LAUNCH_PLAN = "Next step: let {agent} deploy and run the sample pipeline on dltHub for you."
MSG_LAUNCH_PLAN_RESOLVE = "Setup hit an error — let {agent} help resolve it and finish onboarding."


# Errors (call sites use .format() with named placeholders) -------------
ERROR_UNKNOWN_AGENT = "Unknown agent {agent!r} for scaffold {scaffold!r}. Available: {available}"
ERROR_UV_NOT_ON_PATH = "uv was installed, but it is not available on PATH yet. Open a new terminal and try again."
ERROR_UV_COMMAND_FAILED = "Command failed with exit code {returncode}: {cmd}"
ERROR_UV_COMMAND_NOT_FOUND = "Command not found: {cmd}"
ERROR_UV_INSTALLER_FETCH = "Could not download uv installer: {reason}"
ERROR_UV_NEEDS_POWERSHELL = "PowerShell is required to install uv on Windows."
ERROR_UNKNOWN_SCAFFOLD = "Unknown scaffold {scaffold!r}. Available: {available}"
ERROR_PARSE_PYPROJECT = "Could not parse generated pyproject.toml: {reason}"
ERROR_WRITE_FAILED = "Couldn't write to {path}: {reason}"
ERROR_READ_FAILED = "Couldn't read {path}: {reason}"
ERROR_CLIENT_SOURCE_NOT_FOUND = (
    "dlthub-client source not found at {path}. Point --dlthub-client-source at a "
    "runtime/clients/cli checkout (or set DLTHUB_CLIENT_SOURCE)."
)
ERROR_NO_AGENT_NON_INTERACTIVE = (
    "No coding agent selected, and this is a non-interactive run so the agent picker can't be shown. "
    "Re-run with --agent <name>. If you are the coding agent running this command, pick yourself:\n"
    "  Claude Code  → --agent claude\n"
    "  Codex        → --agent codex\n"
    "  Cursor       → --agent cursor"
)


# Status / info messages ------------------------------------------------
# Out-of-band stderr note shown when a hidden dev flag (--setup-only / --scaffold-only) is used.
MSG_TESTING_SHORTCUT_NOTE = (
    "[yellow]Note:[/yellow] --setup-only / --scaffold-only are non-interactive shortcuts for testing/CI. "
    "They cut the guided setup short, so onboarding is incomplete. "
    "Run without them for the full interactive setup."
)
MSG_CANCELLED = "\n[yellow]Cancelled.[/yellow]"
MSG_ERROR_PREFIX = "✗ Error:"
MSG_UNEXPECTED_ERROR = "✗ Unexpected error:"
MSG_UNEXPECTED_ERROR_HINT = "[dim]Re-run with --verbose to see the full traceback.[/dim]"
MSG_RELOCATED = "[yellow]Heads up:[/yellow] {relocated_from} isn't empty — scaffolding into {project_dir} instead."
MSG_PACKAGE_NAME = "Project package name: {package_name}"
MSG_SKIPPED_UV_AND_SYNC = "\n[yellow]Skipped[/yellow] uv install and dependency sync.\n"
MSG_SKIPPED_SYNC = "\n[yellow]Skipped[/yellow] dependency sync.\n"
MSG_ADDING_AGENT_FILES = "Adding {agent} workbench files"
MSG_ADDED_AGENT_FILES = "Added {agent} workbench files"
MSG_LAUNCHING_AGENT = (
    f"\n[bold {config.COLOR_CYAN}]Launching {{agent}}[/bold {config.COLOR_CYAN}] "
    "in {project_dir} — your skills and MCP server are ready.\n"
)
# Setup flow: each sub-step has a running (spinner/active) line and a "done" line it ticks to.
MSG_CREATING_WORKSPACE = "Creating your workspace"
MSG_WORKSPACE_READY = "Workspace ready — dependencies installed in .venv"
MSG_WORKSPACE_CREATED = "Workspace created"
MSG_CONNECTING_DLTHUB = "Connecting to dltHub"
MSG_CONNECTED_DLTHUB = "Logged in and connected to the playground workspace"
MSG_SETUP_FAILED = "✗ Workspace setup hit an error:"
# Panel titles ----------------------------------------------------------
TITLE_BANNER = f"{config.DISTRIBUTION_NAME} v{{version}} [bold {config.COLOR_LIME}](beta)[/bold {config.COLOR_LIME}]"
TITLE_ALL_SET = "You're all set"
TITLE_ALMOST_THERE = "Almost there"
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
    f"  [bold {config.COLOR_CYAN}]uvx {config.DISTRIBUTION_NAME}@latest my-workspace[/bold {config.COLOR_CYAN}]\n\n"
    "[dim]Note for AI agents: initializing a workspace installs AI skills and an "
    "MCP server into the target directory. Run it from that directory and keep "
    "your session there (the workspace root) so they're in scope.[/dim]"
)


# Section labels inside panels and the launch plan ----------------------
LABEL_WHAT_TO_TRY = "What to try next"
LABEL_FINISH_SETUP = "Finish setup"
LABEL_DOCS = "Docs:"
LABEL_WORKSPACE = "Workspace:"
LABEL_PROMPT = "Prompt:"


# Links (URL + its display label) ---------------------------------------
LINK_DOCS_URL = f"https://github.com/{config.GITHUB_ORG}/{config.WORKBENCH_REPO_NAME}/blob/master/README.md"
LINK_DOCS_LABEL = f"github.com/{config.GITHUB_ORG}/{config.WORKBENCH_REPO_NAME}"


# Hint text / badges / taglines -----------------------------------------
HINT_RECOMMENDED_SUFFIX = " [dim](recommended)[/dim]"
HINT_ERROR_SHOWN_ABOVE = "<error shown above>"
HINT_CODEX_SUFFIX = " [dim](or other agents, e.g. Copilot)[/dim]"
HINT_NONE = "(none)"
HINT_BANNER_TAGLINE = "Onboarding"


# Step labels (prose halves of the (label, command) tuples) -------------
STEPS_LABEL_CD = "Change into the workspace:"
STEPS_LABEL_RUN_SAMPLE_SHOP = "Run the sample shop pipeline in dltHub (you'll be prompted to connect/login):"
STEPS_LABEL_VIEW_SAMPLE_SHOP_RUNS = "View runs for the sample shop pipeline:"
STEPS_LABEL_EDIT_PIPELINE = "Edit pipeline.py to swap in your own source, then re-run."
STEPS_LABEL_HANDOFF = "Start your coding agent in {project_dir} and paste this prompt:"
HINT_PROMPT_COPIED = "✓ Already copied to your clipboard — just paste it in."
STEPS_LABEL_INSTALL_UV = "Install uv:"
STEPS_LABEL_INSTALL_DEPS = "Install workspace dependencies:"


# Commands shown to the user (the right halves of the tuples) -----------
CMD_INSTALL_UV_UNIX = "curl -LsSf https://astral.sh/uv/install.sh | sh"
CMD_UV_SYNC = "uv sync"
CMD_DLTHUB_RUN_SAMPLE_SHOP = "uv run dlthub run load_sample_shop"
CMD_DLTHUB_JOB_RUNS_SHOW_SAMPLE_SHOP = "uv run dlthub job runs show pipeline.load_sample_shop"
CMD_CD = "cd {project_dir}"
CMD_DEPLOY_RUN_HANDOFF_PROMPT = (
    "Scaffolding, login, and playground connection are done, and the dltHub AI agent files "
    "are installed in this workspace. To continue in this same session, use the "
    f"`{config.ONE_SHOT_ENTRY_SKILL}` skill to deploy and run the sample pipeline. "
    "The skill is located at {skill_path}."
)
CMD_RESOLVE_HANDOFF_PROMPT = (
    "Workspace setup hit an error during dltHub login / playground connection:\n\n"
    "{error}\n\n"
    "Diagnose and fix it using your dltHub tools and the `dlthub` CLI, then use the "
    f"`{config.ONE_SHOT_ENTRY_SKILL}` skill to deploy and run the sample pipeline. "
    "The skill is located at {skill_path}."
)


# Telemetry -------------------------------------------------------------
MSG_TELEMETRY_NOTICE = (
    "[dim]dlthub-start sends anonymous usage events to help us improve user experience. "
    "Opt out with --no-telemetry, DLTHUB_START_TELEMETRY=0, or DO_NOT_TRACK=1."
)
