# Claude Code + Pyright LSP

*Reference guide — what it does, how to install it, how to fix it when it breaks.*

---

## What it is

Claude Code has a built-in LSP tool that connects to language servers. An **LSP
plugin** is the configuration that tells it which server to use for which file
types. The plugin is config only — you install the actual server binary yourself.

For Python that server is **pyright**, Microsoft's static type checker. It does
two jobs:

1. **Type checking** — reads code without running it and flags type errors. Uses
   your annotations where present, infers where absent.
2. **Semantic code intelligence** — go-to-definition, find-references, hover for
   types. This is the same engine behind Pylance in VS Code.

Job 2 is the reason it matters here.

## Why it changes how Claude Code behaves

Without LSP, Claude finds code with grep. Ask where `resolve_address` is defined
and grep returns the definition, the import, the re-export, and a docstring that
mentions the name — Claude then reads each file to work out which is real.

With LSP it asks the language server and gets the answer. Concretely:

| Question | Without LSP | With LSP |
|---|---|---|
| Where is this defined? | grep, then disambiguate by reading | exact file and line |
| What calls this? | grep, hope the name is unique | complete reference list |
| What type is this? | infer from surrounding code | actual resolved type |
| Did my edit break anything? | run tests and find out | diagnostics pushed into context immediately |

The find-references case is the one that matters most for refactoring: Claude
knows every file that breaks *before* it touches anything.

Per Anthropic's docs, LSP integration provides instant diagnostics after each
edit, code navigation (definition, references, hover), and type information for
symbols.

---

## Install

Three steps. The plugin does **not** bundle the server.

**1. Install the pyright binary**

```bash
npm install -g pyright
```

Or via PyPI:

```bash
uv tool install pyright     # or: pip install pyright
```

Note: the PyPI package is a wrapper around the npm distribution and fetches Node
components on first run. If you already have Node, the npm route avoids the
indirection.

Confirm it's on `$PATH`:

```bash
pyright --version
```

**2. Install the plugin**

Inside a Claude Code session:

```
/plugin install pyright-lsp@claude-plugins-official
```

Or from the shell:

```bash
claude plugin install pyright-lsp@claude-plugins-official
```

Add `--scope project` to commit it to `.claude/settings.json` so collaborators
get it. Default scope is `user` (all your projects).

**3. Reload**

```
/reload-plugins
```

No session restart needed.

---

## Verify it's working

Ask Claude Code to go to the definition of a function in your codebase.

- **Working:** you see `LSP` in the tool output and get an exact file and line.
- **Not working:** you see "let me search through the codebase" followed by
  grep calls.

Second check, more useful: ask for all references to a class before a refactor.
LSP returns a complete list; grep returns whatever matched the string.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Executable not found in $PATH` in the `/plugin` Errors tab | server binary not installed or not on PATH | install pyright, confirm `pyright --version` |
| Plugin installed, Claude still greps | plugin not reloaded | `/reload-plugins` |
| Server silently doesn't start | invalid config, e.g. missing `command` or `extensionToLanguage` | `claude --debug` shows why it was skipped |
| Two plugins claim `.py` | first registered server wins, others never start | `/plugin` shows a warning naming the active one; disable the loser |
| Session sluggish, memory pressure | pyright indexing a large repo | `/plugin disable pyright-lsp@claude-plugins-official`, fall back to grep |

A skipped server doesn't claim its extensions, so another valid server declaring
the same ones still handles those files.

---

## Other languages

Anthropic's docs name `pyright-lsp`, `typescript-lsp`, and `rust-analyzer-lsp`
directly. Third-party write-ups from mid-2026 report the marketplace carrying
more — around eleven, adding Go, C/C++, C#, Java, Kotlin, Lua, PHP, and Swift.
Check `/plugin` → Discover and search `lsp` for the current set; that's
authoritative, the docs table may lag.

**For anything not covered**, wire it up yourself with a `.lsp.json` at the
plugin root:

```json
{
  "elixir": {
    "command": "elixir-ls",
    "extensionToLanguage": {
      ".ex": "elixir",
      ".exs": "elixir"
    }
  }
}
```

Required fields are `command` (must be on PATH) and `extensionToLanguage`.
Useful optional ones:

| Field | Purpose |
|---|---|
| `args` | CLI arguments for the server |
| `env` | environment variables at launch |
| `startupTimeout` | max ms to wait for startup |
| `restartOnCrash` | defaults `true`; set `false` to leave a crashed server down |
| `maxRestarts` | cap restart attempts |
| `diagnostics` | defaults `true`; set `false` to keep navigation but suppress automatic diagnostic injection |

`restartOnCrash` and `shutdownTimeout` need Claude Code v2.1.205+. On earlier
versions setting either caused the server to be skipped entirely at startup,
visible only under `claude --debug`.

You can run several LSP plugins at once in a polyglot repo — one per language.

---

## Commands

```bash
claude plugin install pyright-lsp@claude-plugins-official
claude plugin install pyright-lsp@claude-plugins-official --scope project
claude plugin list                    # installed, version, source, status
claude plugin details pyright-lsp     # components + projected token cost
claude plugin disable pyright-lsp     # keep installed, stop loading
claude plugin enable pyright-lsp
claude plugin uninstall pyright-lsp
claude --debug                        # why a server was skipped
```

In-session: `/plugin`, `/reload-plugins`.

---

## When to turn it off

Heavy servers — pyright, rust-analyzer — hold a project index in memory. On a
large repo or a constrained machine, that's real RAM. If sessions get sluggish
or crash, disable the plugin and grep still works.

Worth watching on low-memory boxes; a non-issue on a modern dev machine.

---

## Related

- `.claude/skills/minimal-footprint/SKILL.md` — the search gate LSP makes viable
- `docs/repo-bloat-reference.md` — why semantic retrieval matters for duplication
- Plugins reference: https://code.claude.com/docs/en/plugins-reference
