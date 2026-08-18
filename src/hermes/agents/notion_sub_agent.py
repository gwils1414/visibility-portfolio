#--Sub agent to connect to the obsidian MCP--#
#this follows along with the best practices of artificial narrow intelligence-#
#meaning , each agent should have a specific job.
#hermes will operate as an orchestrator with a few other tools

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


notion_server = NotionMCP()
toolset = MCPToolset(notion_server.mcp)

notion_agent = Agent(
    model = ollama_model,
    instructions = '',
    system_prompt = '',
    name = 'notion agent',
    model_settings= ModelSettings(
        max_tokens = 10000,
        temperature = 0.5,
        timeout = 30
    ),
    toolsets = [toolset]
)