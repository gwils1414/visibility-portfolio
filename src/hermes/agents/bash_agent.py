#--Bash subagent. Narrow, read-only workspace inspection.--#
#this follows along with the best practices of artificial narrow intelligence-#
#meaning , each agent should have a specific job.
#hermes will operate as an orchestrator and delegate filesystem reads here.

from pydantic_ai import Agent, ModelSettings, settings
from hermes.models.deps import Settings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from hermes.system_prompts.bash_agent_system_prompt import get_bash_agent_system_prompt
from hermes.instructions.bash_agent_instructions import get_bash_agent_instructions
from hermes.tools.filesystem import list_directories, list_workspace, read_file, write_file, insert_into_file
from hermes.tools.bash import Bash
from rich.console import Console

import logging
logger = logging.getLogger(__name__)

console = Console()
from config.paths import PROJ_ROOT
deps = Settings()

#single Bash() instance so the gh repo allowlist is fetched once per process
_bash_executor = Bash()


ollama_model = OpenAIChatModel(
    model_name='gemma4:31b-cloud',
    provider=OllamaProvider(base_url='https://ollama.com/v1', api_key=deps.OLLAMA_API_KEY)
)


bash_agent = Agent(
    model = 'openai-chat:gpt-4.1',
    deps_type = deps.OPENAI_API_KEY,
    instructions = get_bash_agent_instructions(),
    system_prompt = get_bash_agent_system_prompt(),
    name = 'bash agent',
    model_settings= ModelSettings(
        max_tokens = 10000,
        temperature = 0.5,
        timeout = 30)
)


#TODO , the four tools below are `async def` but the underlying `list_workspace` / `read_file` / `write_file` /
#        `insert_into_file` helpers do sync filesystem I/O, which blocks the event loop. If concurrent agents ever share
#        this bash_agent, swap the helpers for `aiofiles` (or run them via `asyncio.to_thread`) so reads/writes don't serialize.
@bash_agent.tool_plain(retries=2, requires_approval=False)
async def list_directories_tool():
    '''
    List the directories available to inspect, as newline-separated names.

    Call this first, before `list_files`. It returns the top-level directories
    you are allowed to browse (dotfolders and excluded dirs like .venv, .git,
    node_modules, __pycache__, secrets are filtered out). Pick one of these
    names and pass it to `list_files(directory)` to see the files inside it.
    Takes no arguments.
    '''
    console.print("[bold yellow]Running list_directories_tool()[/bold yellow]")

    dirs = list_directories()
    return dirs


@bash_agent.tool_plain(retries=2, requires_approval=False)
async def list_files(directory: str):
    '''
    List every readable file inside `directory` as relative paths.

    Parameters:
        - directory: a directory name returned by `list_directories_tool`
          (e.g. "visibility"). Call `list_directories_tool` first to discover
          the valid names — do not invent one.

    Use this when the user asks what files exist, where something lives, or you
    need to discover a path before calling `read_file`. Returns a newline-joined
    string of paths (filtered to safe extensions: .py, .md, .txt, .json, .sql,
    .toml, .yaml, .yml). If the return starts with "Error:", the directory was
    blocked or does not exist — report it verbatim and stop.
    '''
    console.print("[bold yellow]Running list_files()[/bold yellow]")

    files = list_workspace(directory)
    return files



@bash_agent.tool_plain(retries=2, requires_approval=False)
async def read_file_tool(path: str) -> str:
    '''
    Read the contents of a single workspace file at `path`.

    Parameters:
        - path: a workspace-relative file path (e.g. "src/hermes/agents/hermes.py").
          Must be a path returned by `list_files` or otherwise known to exist in
          the workspace. Absolute paths, dotfiles, symlinks, and excluded dirs
          are rejected by the underlying safety layer.

    Use this only after you know the path — call `list_files` first if you are
    guessing. Returns the file text, or an error string starting with "Error:"
    if the path is blocked, missing, or too large (>1MB).
    '''
    console.print("[bold yellow]Running read_file_tool()[/bold yellow]")

    text = read_file(path)
    return text


@bash_agent.tool_plain(retries=2, requires_approval=False)
async def write_file_tool(path: str, content: str) -> str:
    '''
    Create a brand new workspace file at `path` containing `content`.

    Parameters:
        - path: workspace-relative path for the new file (e.g.
          "src/hermes/agents/foo.py"). Must satisfy safe_path: no
          absolute paths, no dotfiles, no symlinks, no excluded dirs,
          and the suffix must be in the allowed set (.py, .md, .txt,
          .json, .sql, .toml, .yaml, .yml).
        - content: full text body to write. Hard cap of 1MB.

    A human-in-the-loop prompt fires before the write — the underlying
    `write_file` shows the path + content and waits for y/n in the
    terminal. If the user declines, the function returns
    "Permission denied" and nothing is written. Parent directories are
    created as needed.

    Use this only for new files. To modify an existing file, call
    `insert_into_file_tool` instead (it preserves existing content).
    Returns a confirmation string, "Permission denied", or an
    "Error:" string on safe_path / size failure.
    '''
    console.print("[bold yellow]Running write_file_tool()[/bold yellow]")

    result = write_file(path, content)
    return result


@bash_agent.tool_plain(retries=2, requires_approval=False)
async def insert_into_file_tool(path: str, content: str, line_number: int) -> str:
    '''
    Insert `content` as a new line at `line_number` inside an existing
    workspace file at `path`.

    Parameters:
        - path: workspace-relative path to an existing file. Must
          satisfy the same safe_path rules as `read_file_tool`.
        - content: the line to insert. A trailing newline is added
          automatically — pass the raw line text.
        - line_number: 0-indexed insertion point. The new line is
          inserted *before* the line currently at this index, so
          line_number=0 prepends to the file and line_number=len(lines)
          appends. Call `read_file_tool` first to count lines and
          choose the right index.

    A human-in-the-loop prompt fires before the write, showing the
    line number and a 100-char preview. If the user declines, the
    function returns "Permission denied" and the file is unchanged.

    Use this for edits to existing files. Do not use it to create
    new files — call `write_file_tool` for that. Returns a
    confirmation string, "Permission denied", or an "Error:" string.
    '''
    console.print("[bold yellow]Running insert_into_file_tool()[/bold yellow]")

    result = insert_into_file(path, content, line_number)
    return result


@bash_agent.tool_plain(retries=2, requires_approval=False)
async def run_subprocess(agent_pass: str) -> str:
    '''
    Execute a single validated `gh` (GitHub CLI) command against the
    operator's GitHub account, with a human-in-the-loop approval step
    before anything runs.

    Parameters:
        - agent_pass: a JSON **string** (not a Python dict) with this
          exact shape — emit it as a JSON-encoded string:

              {
                  "command":     "gh",
                  "sub_command": "issue create",
                  "args": {
                      "--title": "fix the foo",
                      "--body":  "the foo is broken",
                      "--repo":  "aretecp/visibility"
                  }
              }

          The string is parsed with `json.loads` into a dict before any
          validation runs. Malformed JSON raises and the call fails.

    Allowed `command` values:
        - "gh"   (the only one)

    Allowed `sub_command` values and their per-sub_command flag allowlist:
        - "issue create"  → --title, --body, --assignee, --repo
        - "issue list"    → --repo, --state, --limit
        - "label list"    → --repo
        - "repo list"     → (reserved; do not call until further notice)

    Hard constraints enforced by the validator (you cannot bypass them):
        - Any `command` other than "gh" is rejected.
        - Any `sub_command` outside the allowlist is rejected.
        - Any flag not in that sub_command's allowlist is rejected.
        - Any flag *value* that contains a blocked substring is rejected.
          Blocked substrings include: --delete, --admin, --token, &&, ;,
          |, >, <, `, $(, ../, ~/, "secret", "webhook", "deploy".
        - Any flag value longer than 500 characters is rejected.
        - If --repo is present, the value must be a repo the operator
          actually owns / belongs to (fetched live from `gh repo list`).

    Execution flow:
        1. The JSON string is parsed into a dict.
        2. `validate_commands` runs all of the checks above. On failure
           the validator's error string is returned immediately and
           subprocess is NEVER invoked.
        3. The assembled argv (e.g. `["gh","issue","create","--title",...]`)
           is rendered in a yellow Rich panel and the operator is asked
           "Approve? Yes/No" via `questionary`. Declining returns the
           literal string "Cancelled" with no side effects.
        4. On approval, the command runs via `subprocess.run` with
           `shell=False` (no shell interpolation, no piping).

    Returns (always a string — report verbatim, never paraphrase):
        - A validation error like "Sub command not permitted",
          "Flag '--foo' not permitted", "Repo not allowed", or
          "Blocked pattern '...' detected in arguments".
        - "Cancelled" when the operator declined the approval prompt.
        - The command's stdout, or stderr if stdout is empty.
    '''
    console.print("[bold yellow]Running run_subprocess()[/bold yellow]")

    result = _bash_executor.run_subprocess(agent_pass)
    return result
