# How to Convert Hermes CLI → TUI

## Goal

Turn [src/hermes/cli/chat.py](../../cli/chat.py) from a scrolling Rich CLI into a real terminal UI: persistent header/footer, a chat scroll region above a fixed input, modal screens for the model picker and feedback flow, and a background worker so `hermes_agent.run(...)` never freezes the input field.

Framework choice: **Textual** (same authors as Rich). Rich renderables — `Panel`, `Markdown`, `Table`, `ProgressBar`, the eval bars — port in as widget content unchanged, and Textual is async-native so the agent's `async` tools fit without `asyncio.run(...)` per turn.

Drop a second file at `src/hermes/cli/tui.py` rather than overwriting `chat.py`. Keep the CLI runnable while iterating.

---

## Size estimate

Net new code: **~300–400 lines** in `tui.py`, replacing the ~210 lines of loop + banner + questionary modals in `chat.py`.

| Current (`chat.py`) | Textual equivalent | ~Lines |
|---|---|---|
| `print_banner()` at [chat.py:81](../../cli/chat.py#L81) | `Header` + welcome `Static` (or one-shot screen) | ~20 |
| `while True: prompt()` loop at [chat.py:152](../../cli/chat.py#L152) | `on_input_submitted` handler + `VerticalScroll` chat container | ~40 |
| `request_model()` + inline `models` modal | `ModelPickerScreen(ModalScreen)` with `OptionList` | ~30 |
| Feedback flow at [chat.py:182-202](../../cli/chat.py#L182-L202) | Two-step `FeedbackScreen(ModalScreen)` | ~40 |
| Slash command branch at [chat.py:176](../../cli/chat.py#L176) | unchanged — called from input handler | ~5 |
| `console.status("thinking...")` + `asyncio.run(...)` | `run_worker(...)` + `LoadingIndicator` | ~30 |
| Response Panel + eval bars Panel | Custom `HermesMessage(Static)` mounting both | ~50 |

Effort: **half a day to a day** if you've used Textual before, **one weekend** if it's your first Textual app.

---

## The hidden cost — sync stdout from inside agents

This is the part that turns a one-day port into a three-day port. Every agent and tool today writes status breadcrumbs straight to the terminal via `console.print(...)`:

- [hermes.py:52](../../agents/hermes.py#L52), [:81](../../agents/hermes.py#L81), [:100](../../agents/hermes.py#L100), [:161](../../agents/hermes.py#L161) — `Running call_notion_agent()`, `Running call_bash_agent()`, etc.
- [bash_agent.py:54](../../agents/bash_agent.py#L54), [:76](../../agents/bash_agent.py#L76), [:106](../../agents/bash_agent.py#L106), [:137](../../agents/bash_agent.py#L137), [:206](../../agents/bash_agent.py#L206) — `Running list_files()`, `Running read_file_tool()`, etc.
- [bash.py:126](../../tools/bash.py#L126) — `console.print(Panel(...))` for the pending `gh` command preview.

In the current CLI those harmlessly print above the next prompt. **In Textual they corrupt the screen** because anything writing to stdout from inside the app's process bleeds through the rendered frame.

Worse: [Bash.run_subprocess](../../tools/bash.py#L132) does a blocking `questionary.select("Approve?", ...)` on stdin from inside the agent worker. That reads from the same TTY Textual is rendering into. It will deadlock the UI.

The HITL prompt on file writes (`write_file` / `insert_into_file` in [filesystem.py](../../tools/filesystem.py)) has the same problem.

### Two paths

1. **Cheap path — silence the breadcrumbs.**
   Replace every `console.print("[bold yellow]Running X()[/bold yellow]")` with `logfire.info("Running X()")`. Breadcrumbs still exist in Logfire, just not in the terminal. Then route the `questionary` calls to a Textual `ModalScreen` via an asyncio.Event (see below). Total touch: ~10 files, mechanical edits.

2. **Right path — tool event bus.**
   Add a module-level `asyncio.Queue` (or a callback registry) at something like `hermes/observability/events.py`. Tools push events onto it: `{"kind": "tool_start", "name": "list_files", "ts": ...}`. The Textual app subscribes on startup and renders events into a side pane or as inline rows underneath the active `UserMessage` widget. You get a live "agent timeline" for free, and tools stay decoupled from the UI shell. Bigger lift (~100 more lines + touching every tool), but it's the version you'd actually want long-term.

### Bridging the HITL prompts into the TUI

The trick: tools currently call `questionary.select(...)` synchronously. To survive in Textual, that has to become async and yield to the UI.

```python
# in some shared module
_pending_approvals: dict[str, asyncio.Future] = {}

async def request_approval(payload: dict) -> str:
    """Called from a tool. Posts an approval event and awaits the UI's response."""
    fut = asyncio.get_event_loop().create_future()
    request_id = str(uuid.uuid4())
    _pending_approvals[request_id] = fut
    EVENT_BUS.put_nowait({"kind": "approval_request", "id": request_id, "payload": payload})
    return await fut  # "Yes" / "No" / "Cancelled"
```

The Textual app's event subscriber sees `approval_request`, pushes a confirm `ModalScreen` rendering the payload (the assembled `gh` argv, or the file write preview), and when the user picks, calls `_pending_approvals[request_id].set_result(...)`. The tool unblocks. Same pattern handles both `Bash.run_subprocess` and the filesystem write HITL.

---

## File layout — what `tui.py` actually contains

Structure (~280 lines):

1. **Imports + env muting** — same `os.environ[...]` block from `chat.py` top.
2. **`MODEL_LIST` constant** — same `['gpt-oss:120b-cloud','gemma4:31b-cloud']`.
3. **Eval helpers** — `_score_color`, `render_eval_bars` lifted from `chat.py` verbatim.
4. **Message widgets**:
   - `UserMessage(Static)` — Rich Panel with cyan border, timestamp, the user's text.
   - `HermesMessage(Static)` — Rich Panel (green) with `Markdown(output)`, plus a stacked Eval Panel rendering `render_eval_bars(evals)` via `rich.console.Group`.
5. **Modal screens**:
   - `ModelPickerScreen(ModalScreen[Optional[str]])` — `OptionList` over `MODEL_LIST`; dismisses with the chosen model id.
   - `FeedbackScreen(ModalScreen[Optional[dict]])` — two-step: `OptionList` (like/dislike) → swap to an `Input` for the reason → dismiss `{"response": ..., "reason": ...}`.
6. **`HermesApp(App)`**:
   - CSS block (chat region `1fr`, input docked bottom, modals centered).
   - `BINDINGS`: `ctrl+m` → models, `ctrl+f` → feedback, `ctrl+q` → quit.
   - `compose()` → `Header`, `VerticalScroll(id="chat")`, `Vertical(id="input-row") → Input`, `Footer`.
   - `on_mount()` → init `ShortTermMemory`, `Feedback`, generate `session_id`, force first model pick via `push_screen_wait`.
   - `on_input_submitted()` → handles `exit`/slash commands, mounts `UserMessage` + `LoadingIndicator`, calls `self.run_worker(self._do_turn(text), exclusive=True)`.
   - `_do_turn()` async worker → `await hermes_agent.run(...)`, extract tool calls, append to `chat_history`, persist to `short_term_memory`, `await inline_evals(...)`, mount `HermesMessage`.
   - `action_open_models`, `action_open_feedback` → `push_screen_wait` the relevant modal, wire the result back to the agent / DB.
7. **`main()` + `if __name__ == "__main__":`** — `HermesApp().run()`.

### Wire-up options

- Quick: `uv run python -m hermes.cli.tui`.
- Permanent: add `tui = "hermes.cli.tui:main"` under `[project.scripts]` in [pyproject.toml](../../../../pyproject.toml). Keeps `hermes chat` as the CLI; adds `hermes-tui` as the TUI.

---

## Phased approach — how I'd actually do this

**Phase 1 — Working TUI, breadcrumbs silenced. ~1 day.**
1. Create `src/hermes/cli/tui.py` with the structure above.
2. Sweep `console.print("[bold yellow]Running X()[/bold yellow]")` calls → `logfire.info("Running X()")`. Files touched: [hermes.py](../../agents/hermes.py), [bash_agent.py](../../agents/bash_agent.py), [notion_sub_agent.py](../../agents/notion_sub_agent.py), [morning_briefing.py](../../agents/morning_briefing.py).
3. Disable / route around `Bash.run_subprocess` approval — for the first cut, either drop the `gh` tool from `bash_agent` or set a feature flag that bypasses the questionary call when running under the TUI.
4. Ship. The agent works, but the bash agent's `gh` tool is half-disabled.

**Phase 2 — Approval bridge. ~1 day.**
1. Add `hermes/observability/events.py` with the queue + `request_approval` helper.
2. Rewrite [Bash.run_subprocess](../../tools/bash.py#L103) to `await request_approval(...)` instead of `questionary.select(...)`.
3. Rewrite [filesystem.write_file](../../tools/filesystem.py) / [insert_into_file](../../tools/filesystem.py) HITL the same way.
4. Add an event subscriber on `HermesApp` that listens for `approval_request` and pushes a confirm `ModalScreen`.
5. Both CLI and TUI now route approvals the same way. (The CLI subscriber can fall back to `questionary` if you want — same interface, different consumer.)

**Phase 3 — Tool timeline. ~1 day.**
1. Add `tool_start` / `tool_end` events alongside `approval_request` on the same bus.
2. Add a `ToolTimeline` widget docked to the right of `#chat` showing recent tool calls with duration.
3. Optional: when a tool emits an event, find the most recent `UserMessage` and append a single-line breadcrumb under it.

After Phase 3 you have parity with the CLI breadcrumbs, plus richer info, plus a UI that doesn't corrupt itself.

---

## Other sync-blocking landmines to clear

These don't break the TUI but will visibly freeze the input field while the call is in flight. Already flagged as TODOs in the agent files:

- [hermes.py:87-103](../../agents/hermes.py#L87) — `ObsidianTool.read_files()` is sync (psycopg + sklearn cosine). Wrap in `asyncio.to_thread(...)`.
- [morning_briefing.py:40](../../agents/morning_briefing.py#L40) — same shape.
- [bash_agent.py:41-43](../../agents/bash_agent.py#L41) — filesystem helpers do sync I/O. Either `aiofiles` or `asyncio.to_thread`.

In the CLI you don't notice because there's no UI to freeze; in Textual, the cursor stops blinking during the call. Worth doing as a Phase 2 hygiene pass.

---

## Open questions to answer before starting

1. **Do you want `hermes chat` to stay alive?** If yes, this is purely additive — `tui.py` is a sibling, `chat.py` keeps working. If you'd rather collapse to one entry point, plan for a `chat.py` deletion at the end of Phase 1.
2. **Approval modals — block per-call or queue?** If two tools fire approvals concurrently (currently impossible, but the agent fan-out work would change that), do you queue them or render side-by-side? Probably queue, but worth deciding before Phase 2.
3. **Does the tool timeline live in the same window, or a separate pane togglable with a binding?** Affects the CSS layout in Phase 3.
4. **Inline evals — keep stacked under each response, or move to a collapsible drawer?** Stacking is what `chat.py` does today and matches reader expectation; a drawer keeps the chat denser. Cosmetic, decide once you've used it for a day.

---

## References

- Textual docs: <https://textual.textualize.io/> — `App`, `ModalScreen`, `run_worker`, `OptionList`, CSS.
- `chat.py` is the source-of-truth flow being ported: [src/hermes/cli/chat.py](../../cli/chat.py).
- Existing async + tool patterns to match: [hermes.py](../../agents/hermes.py), [bash_agent.py](../../agents/bash_agent.py).
