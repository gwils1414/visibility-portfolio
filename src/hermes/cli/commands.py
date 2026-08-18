#--Placeholder for logic to handle commands via the cli to execute stored skills/commands--#
from pathlib import Path
from hermes.models.deps import Settings
from rich.console import Console

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)

console = Console()
import pandas as pd



#-init-#
deps = Settings()
command_directory = Path(deps.OBSIDIAN_COMMANDS_PATH)
MAX_FILE_SIZE = 2_000_000  # 2MB


@log
def show_all_available_commands():
    #TODO , add help, workflows and so on here.
    directory_paths = list(path for path in command_directory.rglob("*") if path.is_dir())
    commands = ["/"+path.name for path in directory_paths if "references" not in str(path).lower()]
    console.print(f"[bold orange]Available slash commands: [/bold orange]\n[dim]{commands}[/dim]")


@log
def execute_commands(user_input:str):
    directory_paths = list(path for path in command_directory.rglob("*") if path.is_dir())

    if user_input.startswith("/"):
        parts = user_input.rsplit(sep = " ")
        command = parts[0]
        for path in directory_paths:
            if command == "/"+path.name:
                skill = path.absolute() / "SKILL.md"
                return skill.read_text()

        return "No command found"
    
#TODO , read other nested reference files
@log
def read_command_references(path:str):
    '''
    Read linked references as needed

    Pass in paths for references.

    i.e: references/handoff.md
    '''
    #verify safe path
    resolved = (command_directory / path).resolve()
    if not resolved.is_relative_to(command_directory):
        raise PermissionError(f"Path escape blocked: {path}")
    if resolved.is_symlink():
        raise PermissionError(f"Symlinks are not allowed: {path}")

    else:
        p = resolved
        try:
            if not p.exists():
                return f"Error: file not found: {path}"
            if p.stat().st_size > MAX_FILE_SIZE:
                return f"Error: file too large (max {MAX_FILE_SIZE // 1000}KB)"
            if p.suffix == '.csv':
                results = pd.read_csv()
                return results.to_json(orient="records")
            if p.suffix == '.xlsx':
                results = pd.read_excel()
                return results.to_json(orient="records")
            else:
                return p.read_text()
        except PermissionError as e:
            return f"Error: {e}"