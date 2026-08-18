#--PCE subagent. Narrow Python execution inside the Docker sandbox.--#
#following the same artificial-narrow-intelligence pattern as bash_agent:
#one agent, one job. hermes delegates "run this python" here; this agent
#writes code, calls the sandbox tool, iterates on errors, and reports back.

from pydantic_ai import Agent, ModelSettings, settings
from hermes.models.deps import Settings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from hermes.system_prompts.pce_agent_system_prompt import get_pce_agent_system_prompt
from hermes.instructions.pce_agent_instructions import get_pce_agent_instructions
from hermes.tools.pce import execute_python_in_sandbox
from rich.console import Console

import logging
logger = logging.getLogger(__name__)

console = Console()
deps = Settings()


#bigger model for code generation — pandas/numpy/plotly correctness benefits
#from the 120b vs. the 31b that bash_agent uses for routing
ollama_model = OpenAIChatModel(
    model_name='gpt-oss:120b-cloud',
    provider=OllamaProvider(base_url='https://ollama.com/v1', api_key=deps.OLLAMA_API_KEY)
)


pce_agent = Agent(
    model = ollama_model,
    instructions = get_pce_agent_instructions(),
    system_prompt = get_pce_agent_system_prompt(),
    name = 'pce agent',
    model_settings= ModelSettings(
        max_tokens = 10000,
        temperature = 0.3,
        timeout = 60)
)


@pce_agent.tool_plain(retries=2, requires_approval=False)
async def run_python_in_sandbox(code: str) -> str:
    """Run Python code in an isolated Docker sandbox and return its stdout.

    Use this to generate visualizations, run data transforms, or perform any
    one-off Python computation. The code runs inside a locked-down container:
    no network access, non-root user, 512MB memory, 1 CPU, a 128-pid cap, all
    linux capabilities dropped, and a 30-second timeout. The sandbox source
    dir is mounted read-only.

    Only pandas, numpy, and plotly are pre-installed. Because there is no
    network, the code cannot `pip install` anything — work with those three.

    To persist a result (a chart, a CSV, a file), the code must write it into
    the `output/` directory, e.g. `fig.write_image("output/chart.png")` or
    `df.to_csv("output/data.csv")`. That directory maps to the host at
    `src/hermes/sandbox/output/`.

    Returns the captured stdout on success, or an error string on failure
    (code-check rejection, non-zero exit, or the 30s timeout). On error,
    read the message, fix the code, and call again — up to 3 attempts total
    per request.

    Parameters:
        - code: the Python code to execute in the sandbox, passed as a string.
    """
    console.print("[bold yellow]Running run_python_in_sandbox()[/bold yellow]")

    return await execute_python_in_sandbox(code)
