#--Web search subagent. Narrow, network-bounded research helper.--#
#this follows along with the best practices of artificial narrow intelligence-#
#meaning , each agent should have a specific job.
#hermes will operate as an orchestrator and delegate open-web lookups here.

from pydantic_ai import Agent, ModelSettings, settings
from hermes.models.deps import Settings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from hermes.system_prompts.web_search_agent_system_prompt import get_web_search_agent_system_prompt
from hermes.instructions.web_search_agent_instructions import get_web_search_agent_instructions
from hermes.tools.web_search import WebSearch
from rich.console import Console

import logging
logger = logging.getLogger(__name__)

console = Console()
from config.paths import PROJ_ROOT
deps = Settings()
#single WebSearch() instance so validators / state are constructed once per process
_web_search = WebSearch()


ollama_model = OpenAIChatModel(
    model_name='gpt-oss:120b-cloud',
    provider=OllamaProvider(base_url='https://ollama.com/v1', api_key=deps.OLLAMA_API_KEY)
)


web_search_agent = Agent(
    model = ollama_model,
    instructions = get_web_search_agent_instructions(),
    system_prompt = get_web_search_agent_system_prompt(),
    name = 'web search agent',
    model_settings= ModelSettings(
        max_tokens = 10000,
        temperature = 0.3,
        timeout = 60)
)


@web_search_agent.tool_plain(retries=2, requires_approval=False)
async def ddgs_search(query: str) -> str:
    '''
    Run a DuckDuckGo text search and return up to 5 results.

    Parameters:
        - query: short keyword query (under 50 chars). The underlying
          validator rejects longer queries with "Query too long".
          Strip the user's framing — keep the nouns and qualifiers.

    The query is screened for profanity before the search runs; a
    failure returns "Failed profanity check". A terminal y/n prompt
    fires before the network request — "Cancelled" means the user
    declined. On success, returns a list of dicts (title, href, body)
    for the top ~5 hits.

    Use this first for any open-ended lookup. If the snippets answer
    the question, stop here. If a snippet is promising but partial,
    pass its `href` to `fetch_page`.
    '''
    console.print("[bold yellow]Running ddgs_search()[/bold yellow]")

    results = _web_search.ddgs_search(query=query)
    return results


@web_search_agent.tool_plain(retries=2, requires_approval=False)
async def fetch_page(url: str) -> str:
    '''
    Fetch a single web page and return its cleaned visible text.

    Parameters:
        - url: a URL returned by `ddgs_search` this turn, or a URL
          Hermes explicitly handed you. Never invent URLs.

    Strips <script>, <style>, <nav>, <footer>, and <header> tags
    before returning the remaining text. The response goes through a
    profanity check — a failure returns "Failed profanity check". A
    terminal y/n prompt fires before the network request; "Cancelled"
    means the user declined.

    Use this only when a `ddgs_search` snippet is not enough to
    answer. One or two targeted fetches per turn is the norm — do not
    chain through every result.
    '''
    console.print("[bold yellow]Running fetch_page()[/bold yellow]")

    text = _web_search.fetch_page(url=url)
    return text
