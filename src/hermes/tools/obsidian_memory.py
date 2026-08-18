#--Obsidian Memory Interactions--#
#will be pretty similar to the obsidian skills , except no cosine similarity-#
#load MEMORY.md as index on every run , agent can decide which memory files it wants to access from there
#Hermes needs instructions on how to maintain and interact with these files
#this will hinge off reading and writing to the memory path.
from pathlib import Path
from hermes.models.deps import Settings
import questionary
from rich.console import Console
from rich.panel import Panel

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)


console = Console()

#-init-#
deps = Settings()
MEMORY = Path(deps.OBSIDIAN_MEMORY_PATH)
INDEX = MEMORY / "MEMORY.md"


class ObsidianMemoryTool():
    def __init__(self):
        self.memory = MEMORY
        self.index = INDEX

    @log
    def _safe_path(self, file: str) -> Path:
        '''
        Keep writes/reads contained to MEMORY. Only .md files allowed.
        '''
        resolved = (self.memory / file).resolve()
        if not resolved.is_relative_to(self.memory):
            raise PermissionError(f"Path escape blocked: {file}")
        if resolved.suffix != ".md":
            raise PermissionError(f"Only .md files allowed: {file}")
        return resolved

    @log
    def read_index(self) -> str:
        '''
        Load MEMORY.md as the index of all memory files.

        Agent decides which memory files to access from here.
        '''
        try:
            return self.index.read_text()
        except Exception as e:
            print(f"Failed to read MEMORY.md index: {e}")
            return "No index found"

    @log
    def read_memory(self, file: str) -> str:
        '''
        Read a specific memory file from MEMORY.

        file: filename relative to MEMORY (e.g. 'user_role.md')
        '''
        try:
            p = self._safe_path(file)
            if not p.exists():
                return f"Error: memory file not found: {file}"
            return p.read_text()
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            print(f"Failed to read memory file {file}: {e}")
            return f"Error: {e}"
    
    #TODO , review here down
    @log
    def write_memory(self, file: str, content: str) -> str:
        '''
        Write/overwrite a memory file in MEMORY.

        HITL approval required before writing.
        '''
        try:
            p = self._safe_path(file)

            console.print(Panel(
                f"[dim]{content}[/dim]",
                title=f"[yellow]🧠  Memory write → {file}[/yellow]",
                border_style="yellow"
            ))

            approval = questionary.select(
                "Approve memory write?",
                choices=["Yes", "No"]
            ).ask()

            if approval == "Yes":
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
                return f"Memory written to: {p.relative_to(self.memory)}"
            else:
                return "Permission denied"
        except PermissionError as e:
            return f"Error: {e}"

    @log
    def insert_memory(self, file: str, content: str, line_number: int) -> str:
        '''
        Insert content into an existing memory file at a given line.

        Call read_memory first to pick the right line. Use a line past the end
        of the file to append.

        HITL approval required before writing.
        '''
        try:
            p = self._safe_path(file)
            if not p.exists():
                return f"Error: memory file not found: {file}"

            console.print(Panel(
                f"[dim]{content[:300]}{'...' if len(content) > 300 else ''}[/dim]",
                title=f"[yellow]🧠  Memory insert → {file} @ line {line_number}[/yellow]",
                border_style="yellow"
            ))

            approval = questionary.select(
                "Approve memory insert?",
                choices=["Yes", "No"]
            ).ask()

            if approval == "Yes":
                lines = p.read_text().splitlines(keepends=True)
                lines.insert(line_number, content + "\n")
                p.write_text("".join(lines))
                return f"Inserted at line {line_number} in: {p.relative_to(self.memory)}"
            else:
                return "Permission denied"
        except PermissionError as e:
            return f"Error: {e}"

    @log
    def append_to_index(self, entry: str) -> str:
        '''
        Add a one-line pointer to MEMORY.md.

        entry: a single line like '- [Title](file.md) — one-line hook'
        '''
        try:
            console.print(Panel(
                f"[dim]{entry}[/dim]",
                title="[yellow]🧠  Append → MEMORY.md[/yellow]",
                border_style="yellow"
            ))

            approval = questionary.select(
                "Approve index append?",
                choices=["Yes", "No"]
            ).ask()

            if approval == "Yes":
                line = entry if entry.endswith("\n") else entry + "\n"
                with self.index.open("a") as f:
                    f.write(line)
                return f"Appended to MEMORY.md: {entry}"
            else:
                return "Permission denied"
        except Exception as e:
            print(f"Failed to append to MEMORY.md: {e}")
            return f"Error: {e}"
