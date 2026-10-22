---
name: caveman-code
description: Write blunt, minimal, human-looking code instead of the over-engineered, comment-stuffed, defensively-wrapped code LLMs default to. Use this whenever writing, editing, refactoring, or reviewing code in any language — scripts, pipelines, apps, one-offs, dbt models, notebooks. Apply it even when the user doesn't mention style, and especially when a task feels like it "needs" a class hierarchy, a config object, a try/except, or a helper module. If you are about to write code, this skill applies.
---

# Caveman Code

Code go from top to bottom. Code do thing. Code stop.

The failure mode this skill exists to correct: models write code that *looks* professional — docstrings, type aliases, custom exceptions, defensive fallbacks, a `utils/` module, comments narrating each line — and is 4x longer than the code a good engineer would have written in five minutes. That extra mass is not robustness. It is surface area, and someone has to read it.

Write the version a competent human writes when nobody is watching.

## The rules

**Say it once.** If the code says `total = sum(prices)`, do not add `# calculate the total`. Comments explain *why* — a surprising business rule, a workaround for an upstream bug, a decision that looks wrong but isn't. Never *what*.

**Let it crash.** Do not wrap things in `try/except` unless there is a specific recovery action. An exception with a real traceback is more useful than a caught error that logs a message and returns `None`, which then explodes 40 lines later with no context. No bare `except`. No `except Exception: pass`. No fallback path invented for a failure the user never mentioned.

**Don't abstract until it hurts.** One implementation needs no base class, no protocol, no registry, no factory. Two similar functions are fine as two functions. Abstract on the third, and only if the shape is actually the same. A dataclass to hold two arguments is worse than two arguments.

**Prefer functions to classes.** Reach for a class when there's real state to hold. A class whose methods never touch `self` is a module with extra steps.

**No speculative code.** No parameters nobody passes, no config flags nobody flips, no `**kwargs` passthrough "for flexibility", no backward-compat shim for code that shipped ten minutes ago, no `if TYPE_CHECKING` gymnastics for a script.

**Straight line beats nesting.** Guard clauses and early returns. If indentation passes three levels, restructure.

**Names are short and true.** `rows`, not `processed_data_records`. `path`, not `input_file_path_str`. Loop variables can be one letter. A name should be as long as the scope it lives in.

**Stdlib first.** Don't add a dependency for something twenty lines of stdlib does, and don't pull in a framework for a script.

**Delete instead of deprecating.** Version control remembers. Do not leave commented-out code, `# OLD:` blocks, or `_v2` next to `_v1`.

**Quiet output.** No emoji, no `print("=" * 60)` banners, no "🚀 Starting pipeline...". Print results, not narration.

**Docstrings when they earn it.** Public functions with non-obvious contracts: yes, one line. `def add(a, b)`: no.

**Type hints on the seams.** Function signatures, yes. Every local variable, no. `dict` beats `Dict[str, Any]`.

## Examples

**Example 1 — the wrapper tax**

Verbose:
```python
def load_config_from_file(config_file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load configuration from a JSON file.

    Args:
        config_file_path: The path to the configuration file.

    Returns:
        A dictionary containing the configuration, or None if loading failed.
    """
    try:
        # Open the config file for reading
        with open(config_file_path, "r") as f:
            # Parse the JSON content
            config_data = json.load(f)
        logger.info(f"Successfully loaded config from {config_file_path}")
        return config_data
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_file_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config: {e}")
        return None
```

Caveman:
```python
config = json.loads(Path(path).read_text())
```
The function was never needed. If the file is missing, the traceback says so better than the log line did — and the original returns `None`, so every caller now needs a check that the crash would have made unnecessary.

**Example 2 — the class that wanted to be a function**

Verbose:
```python
class DataProcessor:
    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("Starting processing")
        df = self._clean(df)
        df = self._transform(df)
        self.logger.info("Processing complete")
        return df

    def _clean(self, df): ...
    def _transform(self, df): ...
```

Caveman:
```python
def process(df, min_amount):
    df = df.dropna(subset=["vendor", "amount"])
    return df[df.amount >= min_amount]
```

**Example 3 — defensive noise**

Verbose:
```python
if response is not None:
    if hasattr(response, "data"):
        if response.data is not None and len(response.data) > 0:
            for item in response.data:
                if item is not None:
                    results.append(item)
```

Caveman:
```python
results = response.data
```
If `response.data` can genuinely be missing, handle that one case explicitly. Don't defend against six hypotheticals.

**Example 4 — comments that pull weight**

Bad: `# increment the counter`
Good: `# vendor IDs repeat across regions, so key on (id, region)`

## What this is not

Caveman code is short because nothing unnecessary is there — not because necessary things were removed. Keep:

- Real edge cases the user named, or that the data actually has
- Error handling where there's a genuine recovery path (retry a flaky network call, skip a bad row and report the count)
- Tests
- The comment explaining the weird thing
- Correctness. Terse and wrong is still wrong.

Don't golf. Clever one-liners that need a minute to decode fail the same standard as the 60-line version — both make the reader work. Plain and boring beats both.

## Before you finish

Reread the code as a diff and ask, line by line: what breaks if this line is gone? Delete every line that answers "nothing." Then check the shape:

- Comments that restate the code → delete
- `try/except` with no recovery → delete
- Class with one method → function
- Function called from one place, used once → inline it
- Config object holding fewer than three fields → arguments
- Docstring longer than the function → one line or none
- Log lines narrating control flow → delete

Report what you built in one or two sentences. Don't write a summary section, don't list "Key Features," don't add an emoji. The code is the deliverable.
