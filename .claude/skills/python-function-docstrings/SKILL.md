---
name: python-docstrings
description: Write or fix human-readable Google-style docstrings for Python functions and methods -- a short one-line summary plus Args/Returns sections, written the way an experienced engineer would actually write them (not templated AI phrasing). Delegates the actual writing to a Sonnet subagent, which tends to produce more natural prose for this than other models. Use this whenever the user asks to "document", "add docstrings to", "explain", or "write doc comments for" Python code, pastes an undocumented function and asks what it does, or asks to clean up/standardize existing docstrings. Trigger even if they just say "add docstrings" with no other detail, or paste a whole file/module of functions.
---

# Python Docstrings (Sonnet-delegated)

Sonnet models tend to write terser, more natural prose for this specific job than other models do, so this skill delegates the actual docstring-writing to a Sonnet subagent rather than doing it inline. Your job as the orchestrating agent is: gather the code, spawn the subagent with the prompt below, and apply/return its output.

## How to execute

1. Identify the function(s) that need docstrings -- from what the user pasted, or by reading the file(s) they pointed at.
2. Spawn a subagent via the Task tool, pinned to Sonnet, passing it the DOCSTRING_PROMPT below plus the target code.
3. Take the subagent's returned code (docstrings inserted) and either show it inline or write it back to the file, matching however the user framed the request.
4. If the subagent flags a function as too ambiguous to document confidently, surface that flag in your own response rather than silently guessing.

### Spawning the subagent

```
Task(
    subagent_type="general-purpose",
    model="sonnet",  # alias for the current Sonnet generation -- forces this
                      # call onto Sonnet regardless of the model driving the
                      # rest of the session
    description="Write human-sounding docstrings",
    prompt=DOCSTRING_PROMPT + "\n\n---\n\nCode to document:\n\n" + <the code>
)
```

If your Claude Code version's Task tool doesn't accept a `model` override, use a persistent subagent instead: create `.claude/agents/docstring-writer.md` once, with `model: sonnet` in its frontmatter and the DOCSTRING_PROMPT below as its body, then invoke it by name (`subagent_type="docstring-writer"`) going forward.

---

## DOCSTRING_PROMPT (pass this verbatim as the subagent's instructions)

You write concise, human-sounding docstrings for Python functions and methods. The bar: a teammate reads it in two seconds and knows what to pass in and what they get back. Actively avoid generic AI-sounding padding -- docstrings that restate the obvious in full sentences instead of just saying the thing.

### The core problem to avoid

LLM-written docstrings have a tell: every line follows the same inflated template regardless of whether the content needs it.

Robotic (avoid this):
```python
def fetch_active_users(db_conn, min_logins=5):
    """
    This function is used to fetch active users from the database.

    Args:
        db_conn: This parameter represents the database connection object
            that will be used to execute the query.
        min_logins (int): This parameter represents the minimum number of
            logins required for a user to be considered active.

    Returns:
        list: A list containing the return value of the function, which
            represents the fetched user records from the database.
    """
```

Human (write like this):
```python
def fetch_active_users(db_conn, min_logins=5):
    """Fetch users who have logged in at least `min_logins` times.

    Args:
        db_conn: Open connection to run the query against.
        min_logins: Minimum login count to count as active. Defaults to 5.

    Returns:
        Matching user rows, in whatever shape the driver's cursor returns
        (usually tuples or dicts).
    """
```

Same information, half the words, and it reads like a person wrote it. Cut these patterns:

- **Meta-description instead of the fact itself.** "This parameter represents the X used for Y" -> just say what X is: "Minimum login count to count as active."
- **Restating the function/parameter name back at the reader.** "This function is used to fetch active users" -> "Fetch active users."
- **Restating the type as a sentence.** "A list containing the return value, which represents..." -> just describe what's in the list.
- **Hedge/filler phrases:** "in order to", "It is important to note that", "is responsible for", "leverage", "utilize" (say "use"), "essentially", "simply" doing double duty as a hedge.
- **Full sentences for things that need three words.** Fragments are fine and often better: `path: Where to read the file from.` not `path: This parameter specifies the path where the file will be read from.`

If a draft docstring would sound normal read aloud in a stand-up, keep it. If it sounds like it's explaining what a docstring is, cut it down.

### Format

Google-style, in this order:

1. **Summary line** -- one sentence, imperative mood ("Fetch...", "Compute...", "Return..."), no restating the function name back.
2. **Args** -- one line per parameter, name followed by what it actually is. Skip `self`/`cls`.
3. **Returns** -- what the output represents, in plain terms. Omit if the function returns `None` and isn't meant to communicate anything by it.

Add **Raises** only if there's a real, worth-knowing exception contract -- don't speculate about every possible exception.

### On types: don't repeat what the signature already says

If the function has type hints, don't re-state the type in parens in the docstring -- it's redundant with something already visible one line up, and repeating it is itself a robotic tell.

```python
# Has type hints -- omit the type from the docstring:
def resize(image: Image, width: int, height: int) -> Image:
    """Resize an image to the given dimensions.

    Args:
        image: The image to resize.
        width: Target width in pixels.
        height: Target height in pixels.

    Returns:
        A new, resized image. The original is left unmodified.
    """
```

```python
# No type hints -- a plain-language type note earns its place:
def resize(image, width, height):
    """Resize an image to the given dimensions.

    Args:
        image: PIL Image to resize.
        width (int): Target width in pixels.
        height (int): Target height in pixels.

    Returns:
        A new, resized image. The original is left unmodified.
    """
```

### Worked example (multi-return, varargs, no type hints)

Input:
```python
def parse_config(path, *overrides, strict=True):
    config = load_yaml(path)
    warnings = []
    for key, value in overrides:
        if key not in config and strict:
            raise KeyError(f"unknown override key: {key}")
        elif key not in config:
            warnings.append(f"ignored unknown key: {key}")
        config[key] = value
    return config, warnings
```

Output:
```python
def parse_config(path, *overrides, strict=True):
    """Load a YAML config and apply overrides on top of it.

    Args:
        path (str): Path to the YAML file.
        *overrides: (key, value) pairs to apply after loading, in order.
        strict (bool): Raise if an override key isn't already in the
            config. If False, ignore it and warn instead. Defaults to True.

    Returns:
        The merged config dict, plus a list of warning strings for any
        overrides that got ignored (only happens when strict=False).
    """
    config = load_yaml(path)
    warnings = []
    for key, value in overrides:
        if key not in config and strict:
            raise KeyError(f"unknown override key: {key}")
        elif key not in config:
            warnings.append(f"ignored unknown key: {key}")
        config[key] = value
    return config, warnings
```

Notice the Returns line names the actual gotcha (warnings only populate under one condition) instead of just "tuple of dict and list" -- that's the one place worth a full clause. Everything else stays a fragment.

### Reading the signature

- **Type hints present** -- use them to know the type, but don't restate them in the docstring.
- **No type hints** -- infer a plausible type from usage/defaults and note it briefly. If genuinely unclear, describe the shape in words ("a mapping of user id to score") rather than guessing a formal type.
- **`*args` / `**kwargs`** -- say what kind of extra values are expected and where they go, not just "additional arguments."
- **Multiple return values** -- cover each element, in order, in the Returns section.
- **Decorated functions / methods** -- document as callers actually invoke it (skip `self`; for `@property`, describe it like an attribute, not with Args/Returns).

### Existing docstrings

- Accurate existing docstring -> leave it. Don't rewrite for style alone unless asked to standardize the whole file.
- Stale docstring (wrong params/return) -> rewrite to match current signature and body.
- Asked to "standardize" a file -> convert everything (reST `:param:`, NumPy-style, plain comments, robotic AI-style, or nothing) into the format above, keeping any genuinely useful detail that's already there.

### Batch requests

For a whole file or module: work through every function in order, return only code blocks (no long prose between them) unless a function needed a judgment call worth a one-line flag, and note at the end if anything was too ambiguous to document confidently and needs the author's input.

### Output format

Return the full code (with docstrings inserted) for every function you were given, in the same order. If anything was too ambiguous to document confidently, say so in a short note after the code rather than guessing.
