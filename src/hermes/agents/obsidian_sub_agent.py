#--Obsidian subagent. Narrow vault access — brain lookup + memory CRUD.--#
#this follows along with the best practices of artificial narrow intelligence-#
#meaning , each agent should have a specific job.
#hermes will operate as an orchestrator and delegate vault work here.

from pydantic_ai import Agent, ModelSettings, settings
from hermes.models.deps import Settings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from hermes.system_prompts.obsidian_agent_system_prompt import get_obsidian_agent_system_prompt
from hermes.instructions.obsidian_agent_instructions import get_obsidian_agent_instructions
from hermes.tools.obsidian_skills import ObsidianTool
from hermes.tools.obsidian_memory import ObsidianMemoryTool
from rich.console import Console

import logging
logger = logging.getLogger(__name__)

console = Console()
deps = Settings()

#single memory-tool instance so we don't re-resolve paths every call
_memory_tool = ObsidianMemoryTool()


ollama_model = OpenAIChatModel(
    model_name='gpt-oss:120b-cloud',
    provider=OllamaProvider(base_url='https://ollama.com/v1', api_key=deps.OLLAMA_API_KEY)
)


obsidian_agent = Agent(
    model = ollama_model,
    instructions = get_obsidian_agent_instructions(),
    system_prompt = get_obsidian_agent_system_prompt(),
    name = 'obsidian agent',
    model_settings= ModelSettings(
        max_tokens = 10000,
        temperature = 0.5,
        timeout = 30)
)


#TODO , `ObsidianTool.read_files()` is sync (psycopg + sklearn cosine on the main thread) and will block the event loop.
#        once embeddings move to pgvector, this should become async using psycopg's AsyncConnection so parallel sub-agents don't serialize on it.
@obsidian_agent.tool_plain(retries=2, requires_approval=False)
async def obsidian_brain_lookup(user_prompt: str) -> str:
    '''
    Cosine-similarity search over the curated `brain/` notes.

    Embeds `user_prompt`, compares it against the obsidian_embeddings
    table, and returns the full text of the single best-matching note
    if its score is at least 0.4. Otherwise returns "No relevant files".

    Call this once at the start of a turn when Hermes asks for the
    brain check. Read-only.

    Parameters:
        - user_prompt: the raw user prompt to embed and compare.
    '''
    console.print("[bold yellow]Running obsidian_brain_lookup()[/bold yellow]")

    obsidian_tool = ObsidianTool(prompt = user_prompt)
    return obsidian_tool.read_files()


@obsidian_agent.tool_plain(retries=2, requires_approval=False)
async def read_memory_index() -> str:
    '''
    Read MEMORY.md — the master index of all memory files.

    Returns the index text so the agent can decide which memory files
    to load next. No arguments.
    '''
    console.print("[bold yellow]Running read_memory_index()[/bold yellow]")

    return _memory_tool.read_index()


@obsidian_agent.tool_plain(retries=2, requires_approval=False)
async def read_memory_file(file: str) -> str:
    '''
    Read a single memory file from the MEMORY directory.

    Parameters:
        - file: `.md` filename relative to MEMORY (e.g. "preferences.md").
          Path escape and non-`.md` files are rejected by the safe_path
          layer.

    Returns the file text, or an error string starting with "Error:"
    if the path is blocked or the file is missing.
    '''
    console.print("[bold yellow]Running read_memory_file()[/bold yellow]")

    return _memory_tool.read_memory(file)


@obsidian_agent.tool_plain(retries=2, requires_approval=False)
async def write_memory_file(file: str, content: str) -> str:
    '''
    Create (or overwrite) a memory file at `file` with `content`.

    Use ONLY for genuinely new memory files. For edits to existing
    files, prefer `insert_into_memory_file` so prior context is
    preserved.

    Parameters:
        - file: `.md` filename relative to MEMORY.
        - content: full text body to write.

    A human-in-the-loop prompt fires before the write. If the user
    declines, the return value is "Permission denied" and nothing is
    written. Parent directories are created as needed.
    '''
    console.print("[bold yellow]Running write_memory_file()[/bold yellow]")

    return _memory_tool.write_memory(file, content)


@obsidian_agent.tool_plain(retries=2, requires_approval=False)
async def insert_into_memory_file(file: str, content: str, line_number: int) -> str:
    '''
    Insert `content` as a new line at `line_number` inside an existing
    memory file.

    Parameters:
        - file: `.md` filename relative to MEMORY (must already exist).
        - content: the line to insert. A trailing newline is added
          automatically — pass the raw line text.
        - line_number: 0-indexed insertion point. The new line is
          inserted *before* the line currently at this index, so
          line_number=0 prepends and a line past the end appends.
          Call `read_memory_file` first to count lines and choose
          the right index.

    A human-in-the-loop prompt fires before the write, showing the
    line number and a 300-char preview. "Permission denied" means
    the user declined.
    '''
    console.print("[bold yellow]Running insert_into_memory_file()[/bold yellow]")

    return _memory_tool.insert_memory(file, content, line_number)


@obsidian_agent.tool_plain(retries=2, requires_approval=False)
async def append_to_memory_index(entry: str) -> str:
    '''
    Append a single one-line pointer to MEMORY.md.

    Use this right after creating a new topic file with
    `write_memory_file`, so the index stays in sync with what exists.

    Parameters:
        - entry: a single line like
          "- [Title](file.md) — one-line hook".

    A human-in-the-loop prompt fires before the append. "Permission
    denied" means the user declined.
    '''
    console.print("[bold yellow]Running append_to_memory_index()[/bold yellow]")

    return _memory_tool.append_to_index(entry)


