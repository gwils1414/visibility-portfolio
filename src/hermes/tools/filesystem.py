#--Requires approval will be true--#

import subprocess
from pathlib import Path
from typing import Literal
import questionary
from rich.console import Console

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)

console = Console()
from rich.panel import Panel
from rich.syntax import Syntax
import pandas as pd

# TODO: WORKSPACE is anchored to the CWD where the CLI launches, so the file
# list the agent sees shifts depending on where you run from. Consider pinning
# to PROJ_ROOT (from config.paths) so the workspace is stable regardless of CWD.
# REVIEW , so this should be able to read files from any directory it is launched from. Need to make hermes launchable from anywhere
WORKSPACE = Path(".").resolve()
#allow file system to reach the project's parent directory
PARENT = WORKSPACE.parent
ALLOWED_EXTENSIONS = {".py", ".md", ".txt", ".json", ".sql", ".toml", ".yaml", ".yml", ".html"}
EXCLUDED_DIRS = {".venv", ".git",".db", "__pycache__", "node_modules", ".mypy_cache", "__init__.py", ".env", "secrets", "taxes", "SSN"}
MAX_FILE_SIZE = 3_000_000  # 1MB


@log
def list_directories() -> str:
    '''
    return available directories for agents reference

    from here, pass any directory into list_workspace

    '''
    dirs = [
        p
        for p in PARENT.iterdir()
        if p.is_dir()
        and p.name not in EXCLUDED_DIRS
        and not p.name.startswith(".")
    ]

    if dirs:
        return dirs
    else:
        return"No directories found"


@log
def list_workspace(directory:str) -> str:
    '''
    This gives us full control over the directory and types of files the agent can access

    Lose of flexibility but gain of control and auditability.

    List files in a specified directory

    Parameter:
        - directory to list file names for
    '''
    files = []

    # walk every path under directory recursively
    for p in Path(directory).rglob("*"):
        # skip directories, we only want files
        if not p.is_file():
            continue
        # skip anything inside a dotfolder or a dotfile itself
        # parts gives us every component of the path as a tuple
        if any(part.startswith(".") for part in p.parts):
            continue
        # skip explicitly excluded dirs like __pycache__
        if any(part in EXCLUDED_DIRS for part in p.parts):
            continue
        # skip disallowed extensions
        if p.suffix not in ALLOWED_EXTENSIONS:
            continue
        # safe — add the relative path (cleaner than full absolute path)
        files.append(str(p.relative_to(PARENT)))

    return "\n".join(files) if files else "No readable files found"


@log
def safe_path(user_provided: str) -> Path:
    resolved = (PARENT / user_provided).resolve()

    if not resolved.is_relative_to(PARENT):
        raise PermissionError(f"Path escape blocked: {user_provided}")
    if resolved.is_symlink():
        raise PermissionError(f"Symlinks are not allowed: {user_provided}")
    if resolved.name.startswith("."):
        raise PermissionError(f"Dotfiles are off limits: {user_provided}")
    if any(part in EXCLUDED_DIRS for part in resolved.parts):
        raise PermissionError(f"Excluded directory: {user_provided}")
    if resolved.suffix not in ALLOWED_EXTENSIONS:
        raise PermissionError(f"Extension not allowed: {resolved.suffix}")

    return resolved

@log
def read_file(path: str) -> str:
    try:
        p = safe_path(path)
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
        #TODO , HTML, JSON

        else:
            return p.read_text()
    except PermissionError as e:
        return f"Error: {e}"
    
#write to file (human in the loop approval for this one)
@log
def write_file(path: str, content: str) -> str:
    '''
    Writes a brand new file.
    '''
    try:
        #saf path check
        p = safe_path(path)
        if len(content.encode()) > MAX_FILE_SIZE:
            return f"Error: content too large (max {MAX_FILE_SIZE // 1000}KB)"
        
        #if path is safe, move to hitl
        #HITL approval
        console.print(Panel(
            f"[dim]{content}[/dim]",
            title=f"[yellow]✏️  Write request → {path}[/yellow]",
            border_style="yellow"
        ))

        approval = questionary.select(
            "Approve write?",
            choices=["Yes", "No"]
        ).ask()

        #if write confirmed, write content
        if approval == "Yes":
            p.parent.mkdir(parents=True, exist_ok=True)  # create dirs if needed
            p.write_text(content)
            return f"Content: {content} Written to: {p.relative_to(PARENT)}"
        else:
            return "Permission denied"
    except PermissionError as e:
        return f"Error: {e}"
    

@log
def insert_into_file(path: str, content: str, line_number: int) -> str:
    '''
    Will need to call read file first to know which line number to insert on
    Insert into an existing file.
    '''
    try:
        p = safe_path(path)

        console.print(Panel(
            f"[dim]{content}[/dim]",
            title=f"[yellow]✏️  Write request → {path}[/yellow]",
            border_style="yellow"
        ))

        approval = questionary.select(
            "Approve write?",
            choices=["Yes", "No"]
        ).ask()

        #if write confirmed, write content
        if approval == "Yes":
            lines = p.read_text().splitlines(keepends=True)
            lines.insert(line_number, content + "\n")
            p.write_text("".join(lines))
            return f"Inserted at line {line_number} in: {p.relative_to(PARENT)}"
        else:
            return "Permission Denied"
    except PermissionError as e:
        return f"Error: {e}"