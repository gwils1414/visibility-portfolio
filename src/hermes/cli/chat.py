#--CLI entry point--#
import warnings

import logging
from hermes.logs.logging_helper import configure as configure_logging, log
configure_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore")
import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # common one too
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["TQDM_DISABLE"] = "1"
import typer
import asyncio
import nest_asyncio
import logfire
logfire.configure()
logfire.instrument_pydantic_ai()
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from hermes.agents.hermes import hermes_agent
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
nest_asyncio.apply()
from prompt_toolkit import prompt #gives us more capabilities in the terminal
from prompt_toolkit.styles import Style
from pyfiglet import figlet_format
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.progress import ProgressBar
from datetime import datetime
from types import SimpleNamespace
from hermes.models.deps import Settings
from hermes.agents.helpers import generate_ollama_model
import questionary
from hermes.cli.commands import execute_commands, show_all_available_commands
from hermes.evals.inline_evals import inline_evals
from hermes.db.memory.short_term import ShortTermMemory
from hermes.db.feedback import Feedback

#--Setup--#

deps = Settings()
app = typer.Typer()
console = Console()
short_term_memory = ShortTermMemory()
feedback = Feedback()
model_list = ['gpt-oss:120b-cloud','gemma4:31b-cloud', 'openai-chat:gpt-4.1']
command_path = deps.OBSIDIAN_COMMANDS_PATH


#TODO , add a --help command or intro command list
#All these functions should probably live in a helper file


@log
def _score_color(score: float) -> str:
    #green = passing, yellow = borderline, red = bad. tweak thresholds to taste.
    if score >= 0.8:
        return "green"
    if score >= 0.5:
        return "yellow"
    return "red"


@log
def render_eval_bars(evals: dict) -> Table:
    """Render an eval-score dict ({'hallucination': 0.8, 'factualness': 0.6, ...}) as colored 0-1 bars."""
    table = Table.grid(padding=(0, 2))
    table.add_column("metric", style="bold")
    table.add_column("bar")
    table.add_column("score")

    for metric, score in evals.items():
        if isinstance(score, (int, float)):
            color = _score_color(score)
            bar = ProgressBar(total=1.0, completed=score, width=40, complete_style=color, finished_style=color)
            table.add_row(metric, bar, f"{score:.2f}")
        else:
            #handles the error fallback from inline_evals where values may be None / strings
            table.add_row(metric, "", str(score))
    return table


from rich.console import Group
from rich.align import Align

@log
def print_banner():
    art = figlet_format("HERMES", font="slant")

    commands = Table.grid(padding=(0, 2))
    commands.add_column(style="bold cyan", no_wrap=True)
    commands.add_column(style="dim")

    commands.add_row("workflows",    "Open workflows menu")
    commands.add_row("commands",    "Show available commands")
    commands.add_row("memory",   "Update long term memory")
    commands.add_row("models",   "Choose a model")
    commands.add_row("feedback", "Provide feedback on a response")
    commands.add_row("exit",   "Quit Hermes")


    #add slash commands here

    content = Group(
        Align.center(f"[bold blue]{art}[/bold blue]"),
        Align.center("[dim]Personal Management Agent[/dim]\n"),
        Rule(style="blue dim"),
        "\n",
        Align.center(commands),
    )

    panel = Panel(
        content,
        border_style="blue",
        padding=(1, 4),
        title="[dim blue]Commands[/dim blue]",
        title_align="right",
        width=200
    )

    console.print(Align.center(panel))

@log
def request_model():
    model_name = questionary.select(
        "Choose a model:",
        choices=model_list
    ).ask()
    
    if model_name in ['gpt-oss:120b-cloud','gemma4:31b-cloud']:
        model = generate_ollama_model(model_name)
        hermes_agent.model = model
        hermes_agent.deps = deps.OLLAMA_API_KEY
    else:
        hermes_agent.model = model_name
        hermes_agent.deps = deps.OPENAI_API_KEY


@log
def panel(body: str,
        time_str = datetime.now().strftime("%H:%M")) -> Panel:
    return Panel(
        Markdown(body),
        title=f"[bold green]Hermes[/bold green] [dim]{time_str}[/dim]",
        border_style="green",
        padding=(1, 2),
    )

@log
async def agent_run(user_input: str, message_history):
    text = ""

    with Live(Markdown(""), console=console, refresh_per_second=15, transient=True) as live:
        async with hermes_agent.run_stream(
            user_prompt=user_input,
            message_history=message_history,
        ) as stream:
            async for chunk in stream.stream_text(delta=True):
                text += chunk
                live.update(Markdown(text))

            output = await stream.get_output()
            new_messages = stream.new_messages()
            all_messages_json = stream.all_messages_json()
            usage = stream.usage

    #TODO , add usage print inline
    console.print(panel(text))

    #prevents of from defining a dataclass
    return SimpleNamespace(
        output=output,
        new_messages=new_messages,
        all_messages_json=all_messages_json,
        usage=usage
    )

#create a cli chat command
@app.command()
def chat():
    """
    Start an interactive chat session with Hermes
    """
    #intro banner
    print_banner()

    #model choice
    request_model()

    #create short term memory table if doesnt exist
    short_term_memory.create_st_schema()

    #create feedback table
    feedback.create_feedback_table()

    #in memory history for now
    #TODO , pass this in from memory instead of hitting the db everytime.
    chat_history:list = []
    session_id = short_term_memory.generate_session_id()


    while True:
        #prompts for user input
        style = Style.from_dict({
            "prompt": "bold cyan",
        })

        user_input = prompt("You: ", style=style)


        if user_input.lower() in ("exit","quit","q"):
            console.print("[dim]Goodbye[/dim]")
            break

        #TODO , can we make this a query to short term memory
        if user_input.lower() == "memory":
            asyncio.run(hermes_agent.run(user_prompt=f"""
                                        Evaluate this current conversation using message histroy
                                        Use the call_short_term_memory() tool to pull session history
                                        for this session {session_id}, and either update your current obsidain
                                        memory files with any pertitent user information or create a new file.
                                        Some things to look for (non-comprehensive)
                                            - technology choices
                                            - structured ways of doings things
                                            - positive responses such as 'great'
                                            - things the user was unhappy with
                                            - tool calling methods or orders to get the right solution
                                        """))
            console.print(panel("Memory evaluated"))

        if user_input.lower() == "models":
            #questionary, select a model from model_list
            model_name = questionary.select(
                "Choose a model:",
                choices=model_list
            ).ask()
            #generate ollama model
            model = generate_ollama_model(model_name)
            #setting model
            hermes_agent.model = model
            continue

        if user_input.lower() == "commands":
            show_all_available_commands()
            continue


        if user_input.lower().startswith("/") and user_input.lower() not in ['/commands', '/help']:
            #TODO, slash command logic here
            command_result = execute_commands(user_input)
            #include as used prompt if slash command is used
            user_input = f"{user_input}\n\nUse read_command_references for any referenced files. Command output:\n{command_result}."

        if user_input.lower() == 'feedback':
                response = questionary.select(
                "How was that response?",
                choices=["👍 Like", "👎 Dislike"],
            ).ask()

                if response is None:
                    return

                reason = questionary.text(
                    "reasoning?",
                    default="",
                ).ask()

                feedback.store_feedback(
                    session_id=session_id,
                    response=response,
                    status='pending_review',
                    reason=reason or None,  # store None if they left it blank
                )
                print("Got it, thanks!\n")

            

        else:
            try:
                #resets at each turn
                tool_calls = []
                result = asyncio.run(agent_run(user_input=user_input,
                                message_history=chat_history))

                console.print()
                console.print(Rule(style="dim"))
                console.print(f"Usage:  {result.usage}")

                #extract tool call parts
                for message in result.new_messages:
                    if hasattr(message, 'parts'):
                        for part in message.parts:
                            if hasattr(part, 'tool_name'):
                                tool_calls.append(part.tool_name)

                #Memory in RAM. Prevents us from hitting the db everytime.
                #TODO, convert this to redis
                messages_json = ModelMessagesTypeAdapter.dump_json(result.new_messages)
                chat_history += ModelMessagesTypeAdapter.validate_json(messages_json)


                #persistent memory
                #TODO : implement the logic
                #if we need to restore a session
                short_term_memory.store_st_memory(session_id=session_id,
                                                user_prompt=user_input,
                                                response=result.output,
                                                tool_calls=tool_calls,
                                                messages = result.all_messages_json.decode('utf-8'))
                
                #inline evals
                evals = asyncio.run(inline_evals(user_input,result.output))
                console.print(Panel(
                    render_eval_bars(evals),
                    title=f"[bold green]Evaluations[/bold green]",
                ))


            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] {e}\n")
if __name__ == "__main__":
    app()