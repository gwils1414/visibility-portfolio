# Hermes CLI Chat Interface — Build Plan

## Overview
Turn the Hermes pydantic-ai agent into an interactive terminal chat interface with real-time tool call visibility using `rich` and `typer`.

---

## Stack
| Library | Role |
|---|---|
| `typer` | CLI entry point and argument parsing |
| `rich` | Colored output, markdown rendering, spinners |
| `pydantic-ai` | Agent + tool execution |
| `fastmcp` | Notion MCP toolset |

---

## Project Structure
```
hermes/
  cli/
    __init__.py
    chat.py          ← main chat loop
    display.py       ← rich console helpers
  agents/
    hermes.py        ← existing agent
  mcps/
    notion_mcp.py    ← existing MCP
```

---

## 1. Entry Point (`chat.py`)

The core is a `while True` loop that:
1. Prompts for user input
2. Runs the agent with message history
3. Prints the response as markdown

```python
import typer
import asyncio
from rich.console import Console
from rich.markdown import Markdown
from hermes.agents.hermes import hermes_agent

app = typer.Typer()
console = Console()

@app.command()
def chat():
    """Start an interactive chat session with Hermes"""
    console.print("[bold blue]Hermes[/bold blue] — type 'exit' to quit\n")

    history = []

    while True:
        user_input = typer.prompt("You")

        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye[/dim]")
            break

        with console.status("[dim]thinking...[/dim]"):
            result = asyncio.run(
                hermes_agent.run(user_input, message_history=history)
            )

        console.print(f"\n[bold green]Hermes:[/bold green]")
        console.print(Markdown(result.output))
        console.print()

        history = result.all_messages()
```

---

## 2. Showing Tool Calls (`display.py`)

Two approaches — use both together:

### A. Inside MCP tools (real-time, shows as tools execute)
```python
# notion_mcp.py
from rich.console import Console
console = Console()

def get_pages(self) -> list[dict]:
    console.print("[dim]  → get_pages()[/dim]")
    result = self.sources.query(data_source_id=self.datasource_id)
    pages = parse_tasks(result.get("results", []))
    console.print(f"[dim]  ← {len(pages)} tasks returned[/dim]")
    return pages

def create_task(self, task_title: str, ...) -> dict:
    console.print(f"[dim]  → create_task('{task_title}')[/dim]")
    # ...
    console.print("[dim]  ← task created[/dim]")
    return "page created"

def update_task(self, page_id: str, ...) -> dict:
    console.print(f"[dim]  → update_task(page_id='{page_id}')[/dim]")
    # ...
    console.print("[dim]  ← task updated[/dim]")
```

### B. From agent messages (after response, full trace)
```python
# optional debug mode in chat.py
for msg in result.all_messages():
    console.print(f"[dim]{msg}[/dim]")
```

---

## 3. What it Looks Like in the Terminal

```
Hermes — type 'exit' to quit

You: what are my open tasks
  thinking...
  → get_pages()
  ← 12 tasks returned

Hermes:
Here are your open tasks:

- **Hermes Agent** — In progress
- **AreteOS Contributions** — In progress
- **Dev team best practices guide** — Not started

You: mark hermes agent as done
  thinking...
  → get_pages()
  ← 12 tasks returned
  → update_task('365bbf8b-ff1a-818a...')
  ← task updated

Hermes:
Done — the Hermes Agent task has been marked as **Done**.

You: exit
Goodbye
```

---

## 4. Memory Across Turns

Pass `message_history` on every agent call so the model remembers context:

```python
# first turn
result = await hermes_agent.run("what are my tasks", message_history=[])

# subsequent turns
result = await hermes_agent.run("mark the first one as done", message_history=result.all_messages())
```

Without this every message is a fresh conversation with no context.

---

## 5. pyproject.toml — Make it a CLI Command

```toml
[project.scripts]
hermes = "hermes.cli.chat:app"
```

After `pip install -e .`:
```bash
hermes        # starts chat
```

---

## 6. Build Order

1. `display.py` — set up console helpers and color scheme
2. Add `console.print` to MCP tool methods
3. `chat.py` — build the chat loop
4. Wire `message_history` for multi-turn memory
5. Register in `pyproject.toml`
6. Test end-to-end with a few task queries

---

## Nice to Have (Later)
- `--debug` flag to toggle full message trace
- Session logging to a file
- `hermes tasks` as a standalone command to just list tasks without chat
- Streaming responses if the model supports it
