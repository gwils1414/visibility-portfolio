#--This is our morning briefing agent. The initial idea behind this--#

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
import fastmcp
from config.paths import PROJ_ROOT

import logging
logger = logging.getLogger(__name__)

deps = Settings()


ollama_model = OpenAIChatModel(
    model_name='gpt-oss:120b-cloud',
    provider=OllamaProvider(base_url='https://ollama.com/v1', api_key=deps.OLLAMA_API_KEY)  
)


morning_briefing = Agent(
    model = ollama_model,
    instructions = '',
    system_prompt = '',
    name = 'morning brief agent',
    model_settings= ModelSettings(
        max_tokens = 10000,
        temperature = 0.5,
        timeout = 30)
)


#TODO , the three tools below are `async def` but their `query_*` helpers use sync `pd.read_sql` on a psycopg connection,
#        which blocks the event loop. Switch the query helpers to psycopg's AsyncConnection (no driver change) so the
#        briefing agent can fan out commit / issue / notion pulls concurrently instead of serializing them.
@morning_briefing.tool_plain(retries=2, requires_approval=False)
async def commit_details():
    '''
    Call to retrieve github commit details
    '''
    return query_commit_details()

@morning_briefing.tool_plain(retries=2, requires_approval=False)
async def issue_details():
    '''
    Call to retrieve github issue details
    '''
    return query_issues()

#dont want this as part of the MCP, runs on a pipeline for my morning brief
#and costs no llm tokens , just hardware
@morning_briefing.tool_plain(retries=2, requires_approval=False)
async def notion_tasks():
    '''
    Call to retrieve notion tasks
    '''
    return query_notion_tasks()