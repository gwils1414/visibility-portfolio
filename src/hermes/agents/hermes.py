from pydantic_ai import Agent, ModelSettings, settings
from hermes.models.deps import Settings
from hermes.tools.query_github_stats import query_commit_details, query_issues
from hermes.tools.query_notion_tasks import query_notion_tasks
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from hermes.system_prompts.hermes_system_prompt import get_hermes_system_prompt
from hermes.instructions.hermes_instructions import get_hermes_instructions
from pydantic_ai.mcp import MCPToolset
from hermes.mcps.notion_mcp import NotionMCP
from hermes.agents.notion_sub_agent import notion_agent
from hermes.agents.morning_briefing import morning_briefing
from hermes.agents.bash_agent import bash_agent
from hermes.agents.pce_agent import pce_agent
from hermes.agents.obsidian_sub_agent import obsidian_agent
from hermes.agents.web_search_agent import web_search_agent
from hermes.tools.spin_up_sub_agent import sub_agent
import fastmcp
from config.paths import PROJ_ROOT
from rich.console import Console

import logging
logger = logging.getLogger(__name__)

console = Console()
deps = Settings()

ollama_model = OpenAIChatModel(
    model_name='gpt-oss:120b-cloud',
    provider=OllamaProvider(base_url='https://ollama.com/v1', api_key=deps.OLLAMA_API_KEY)  
)


#pass in model at runtime in the cli
hermes_agent = Agent(
    #model = ollama_model,
    instructions = get_hermes_instructions(),
    system_prompt = get_hermes_system_prompt(),
    #deps = deps.ANTRHOPIC_API_KEY,
    name = 'Hermes',
    description = 'The hermes agent',
    model_settings= ModelSettings(
        max_tokens = 10000,
        temperature = 0.5,
        timeout = 50
    ))

#TODO , I am thinking we have an agent that does the bash tools
# another that does obsidian brain

@hermes_agent.tool_plain
async def call_notion_agent(prompt: str) -> str:
    """Call the notion sub agent with a prompt and return its response.
    
    Call this tool for any notion related task updates / creation / task list / delete
    """
    console.print("[bold yellow]Running call_notion_agent()[/bold yellow]")

    result = await notion_agent.run(prompt)
    return result.output

@hermes_agent.tool_plain
async def call_morning_briefing(prompt: str) -> str:
    """Call the morning briefing sub agent with a prompt and return its response.
        """
    console.print("[bold yellow]Running call_morning_brief_agent()[/bold yellow]")

    result = await morning_briefing.run(prompt)
    return result.output


@hermes_agent.tool_plain
async def call_bash_agent(prompt: str) -> str:
    """Call the bash sub agent with a prompt and return its response.

    Delegate any workspace filesystem work here: listing files, reading a
    specific file, creating a new file, or inserting a line into an existing
    file. The bash agent has no delete/overwrite tool, and every write fires
    a terminal y/n confirmation before touching disk.

    Pass the user's intent through as-is (e.g. "list every python file under
    src/hermes", "read src/hermes/agents/hermes.py", "create a new file at
    docs/notes.md with this content..."). Do not pre-resolve paths or line
    numbers yourself; let the sub-agent run the discovery → read → write flow.
    """
    console.print("[bold yellow]Running call_bash_agent()[/bold yellow]")

    result = await bash_agent.run(prompt)
    return result.output


@hermes_agent.tool_plain
async def call_obsidian_agent(prompt: str) -> str:
    """Call the obsidian sub agent with a prompt and return its response.

    Delegate any Obsidian-vault work here: the brain check at the
    start of a turn (cosine similarity over the curated `brain/`
    notes), reading from the `memory/` tier (MEMORY.md + topic
    files), and writing observed preferences / project context /
    session notes into `memory/`.

    The obsidian sub-agent has six tools: `obsidian_brain_lookup`,
    `read_memory_index`, `read_memory_file`, `write_memory_file`,
    `insert_into_memory_file`, `append_to_memory_index`. You do not
    call these directly. Every write fires a terminal y/n
    confirmation before touching disk.

    ALWAYS prefix `prompt` with one of these verbs so the sub-agent
    knows which tool to reach for:
      - `"brain check: <raw user prompt>"` — start-of-turn cosine
        similarity over curated brain/ notes. This is the default
        for every user turn.
      - `"memory read: <what you want>"` — read MEMORY.md and/or
        specific memory files.
      - `"memory write: <what to remember and where>"` — write or
        insert into a memory file. Describe the observation and the
        destination tier (preferences / projects / session log /
        new topic); let the sub-agent resolve filenames and line
        numbers.

    Call this at the beginning of each user turn with
    `"brain check: <raw user prompt>"`. If the sub-agent returns
    relevant context, use it; if it returns "No relevant files",
    proceed without it. Call again later in the turn with a
    `memory write:` prefix when the user reveals a preference,
    project decision, or end-of-session note worth remembering.
    """
    console.print("[bold yellow]Running call_obsidian_agent()[/bold yellow]")

    result = await obsidian_agent.run(prompt)
    return result.output

from typing import Literal

@hermes_agent.tool_plain(retries=2, requires_approval=False)
async def spin_up_sub_agent(agent_name:str,
                    instructions:str, 
                    user_prompt:str,
                    model:Literal['gpt-oss:120b-cloud','gemma4:31b-cloud']):
                    """
                    This is your tool to spin up a sub agent if you want to..
                    1. cross reference a theory
                    2. work on something in parallel

                    For example, 3 agents all research the best way to build a data pipeline
                    All 3 agents return their responses, and you cross reference which responses are consitent, or diverge across the results.
                    This helps better educate you for any other decision making.

                    Parameters:
                    - agent_name : name of the agent you are calling
                    - instructions: instructions you want to pass to the agent
                    - user_prompt: what you want the agent to do
                    - model: model you want to use
                    """
                    console.print("[bold yellow]Running obsidian_brain()[/bold yellow]")

                    result = await sub_agent(agent_name,
                                            instructions,
                                            user_prompt,
                                            model)
                    return result
@hermes_agent.tool_plain
async def call_short_term_memory(session_id: str) -> str:
    """Query the short term memory table for a specific session.
    
    Pass the session_id as a string to retrieve the history of prompts, 
    responses, and tool calls for that session.
    """
    console.print("[bold yellow]Running call_short_term_memory()[/bold yellow]")
    from uuid import UUID
    from hermes.db.memory.short_term import ShortTermMemory
    
    try:
        st_memory = ShortTermMemory()
        history = st_memory.retrieve_st_memory(UUID(session_id))
        return str(history)
    except Exception as e:
        return f"Error retrieving short term memory: {e}"

@hermes_agent.tool_plain
async def call_web_search_agent(prompt: str) -> str:
    """Call the web search sub agent with a prompt and return its response.

    Delegate any open-web lookup here: current facts, documentation
    searches, topic research, or fetching the body of a specific public
    URL. The web search sub-agent has two tools: `ddgs_search`
    (DuckDuckGo text search returning ~5 snippet results) and
    `fetch_page` (HTTP GET that returns cleaned page text). Every call
    fires a terminal y/n confirmation before the network request.

    Pass the user's intent through as-is (e.g. "latest pydantic-ai
    release notes", "what does the kubelet --eviction-hard flag do",
    "summarize this URL: https://..."). Do not pre-resolve URLs or
    pre-shape the search query yourself; let the sub-agent build the
    query and choose whether snippets are enough or a fetch is needed.

    If the sub-agent returns "Cancelled", "Failed profanity check",
    "Failed query validation check", or "Query too long", the call did
    not succeed — report that plainly and stop. Do not retry.
    """
    console.print("[bold yellow]Running call_web_search_agent()[/bold yellow]")

    result = await web_search_agent.run(prompt)
    return result.output


@hermes_agent.tool_plain
async def call_pce_agent(prompt: str) -> str:
    """Call the PCE (Python Code Execution) sub agent with a prompt and return its response.

    Delegate any task that needs to actually run Python here: generating a
    visualization (chart/plot), running a data transform, or performing a
    one-off numeric computation. The PCE sub-agent writes the code, runs it
    inside a locked-down Docker sandbox (no network, pandas/numpy/plotly
    only, 512MB / 1 CPU / 30s timeout, writable only to `output/`), and
    iterates on errors before reporting back.

    Pass the user's intent through as-is (e.g. "plot last week's commits by
    day", "compute the mean of column X in this CSV", "make a bar chart of
    these three values"). Do not pre-write the Python yourself — let the
    sub-agent author and iterate on the code.

    Any artifact lands at `src/hermes/sandbox/output/<name>.<ext>`. If the
    user wants to see the produced file, route a read-back through
    `call_bash_agent`.
    """
    console.print("[bold yellow]Running call_pce_agent()[/bold yellow]")

    result = await pce_agent.run(prompt)
    return result.output


from hermes.cli.commands import read_command_references
#TODO read nested references files from commands
@hermes_agent.tool_plain
async def read_commands_reference_files(path:str):
    '''
    Used to read references nested inside of skill.md files read via commands.

    example:
        Present next-step options and execute the user's selection. Read [[references/handoff.md]] for the option logic, dispatch instructions, and closing summary format.

    path:
        references/handoff.md
    
    '''
    result = read_command_references(path=path)
    return result