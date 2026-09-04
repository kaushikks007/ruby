from typing import Optional, Dict, Any
from rich.console import Console
from rich.prompt import Prompt

from ruby.os_control.app_launcher import AppLauncher
from ruby.os_control.file_ops import ScopedFileManager
from ruby.os_control.script_runner import ScriptRunner

console = Console()
_app_launcher = AppLauncher()
_file_mgr = ScopedFileManager()
_script_runner = ScriptRunner()


def launch_app(app_name: str, args: Optional[str] = None) -> str:
    """Narrates and launches a Windows desktop application."""
    console.print(f"\n[bold magenta]⚡ Narrating Plan:[/bold magenta] Opening {app_name} on your PC — one sec.\n")
    ok, msg = _app_launcher.launch(app_name, args)
    if ok:
        return msg
    return f"Failed to launch application: {msg}"


def read_memory_file(relative_path: str) -> str:
    """Reads a file stored in Ruby's memory folder."""
    ok, content = _file_mgr.read_file(relative_path)
    if ok:
        return f"File content of '{relative_path}':\n\n{content}"
    return f"Could not read file: {content}"


def write_memory_file(relative_path: str, content: str, append: bool = False) -> str:
    """Creates or updates a file stored in Ruby's memory folder."""
    ok, msg = _file_mgr.write_file(relative_path, content, append=append)
    if ok:
        return msg
    return f"Failed to write file: {msg}"


def delete_memory_file(relative_path: str, pre_approved: bool = False) -> str:
    """Deletes a file inside Ruby's memory folder with confirmation safeguard."""
    if not pre_approved:
        console.print(f"\n[bold red]⚠️  DESTRUCTIVE ACTION CONFIRMATION[/bold red]")
        console.print(f"File to delete: [bold yellow]{relative_path}[/bold yellow]")
        try:
            confirm = Prompt.ask("Are you sure you want to delete this file? (y/n)", default="n").strip().lower()
        except Exception:
            confirm = "n"

        if confirm not in ["y", "yes"]:
            return f"Action cancelled: File '{relative_path}' was NOT deleted."

    ok, msg = _file_mgr.delete_file(relative_path)
    return msg


def execute_script(script_name: str, args: Optional[str] = None, pre_approved: bool = False) -> str:
    """Runs a script located in Ruby's scripts/ folder with safety check."""
    console.print(f"\n[bold magenta]⚡ Narrating Plan:[/bold magenta] Running script '{script_name}' — one sec.\n")
    
    # Check if script contains potentially destructive commands
    if not pre_approved and _script_runner.is_potentially_destructive(script_name + " " + (args or "")):
        console.print(f"\n[bold yellow]⚠️  SCRIPT CONFIRMATION REQUIRED[/bold yellow]")
        console.print(f"Script: [bold cyan]{script_name}[/bold cyan]")
        console.print(f"Arguments: [bold white]{args or 'none'}[/bold white]")
        try:
            confirm = Prompt.ask("Confirm running this script? (y/n)", default="y").strip().lower()
        except Exception:
            confirm = "y"

        if confirm not in ["y", "yes"]:
            return f"Cancelled: Script '{script_name}' was NOT executed (declined by user)."

    ok, msg = _script_runner.run_script(script_name, args)
    return msg


# Anthropic Claude Tool Definitions
LAUNCH_APP_TOOL = {
    "name": "launch_app",
    "description": "Open or launch a desktop application on kaushik's Windows PC (e.g. 'vscode', 'notepad', 'calculator', 'chrome', 'spotify', 'terminal').",
    "input_schema": {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "Name or alias of the application to open (e.g., 'notepad', 'code', 'calc', 'chrome')."
            },
            "args": {
                "type": "string",
                "description": "Optional command-line arguments or file path to open with the app."
            }
        },
        "required": ["app_name"]
    }
}

READ_MEMORY_FILE_TOOL = {
    "name": "read_memory_file",
    "description": "Read a text or markdown file stored in Ruby's memory folder (C:\\Users\\sudha\\OneDrive\\ruby\\memory).",
    "input_schema": {
        "type": "object",
        "properties": {
            "relative_path": {
                "type": "string",
                "description": "Relative path to the file inside memory/ (e.g. 'projects/hackathon.md', 'profile.json')."
            }
        },
        "required": ["relative_path"]
    }
}

WRITE_MEMORY_FILE_TOOL = {
    "name": "write_memory_file",
    "description": "Create, write, or append text to a file in Ruby's memory folder (C:\\Users\\sudha\\OneDrive\\ruby\\memory).",
    "input_schema": {
        "type": "object",
        "properties": {
            "relative_path": {
                "type": "string",
                "description": "Relative path inside memory/ to save the file."
            },
            "content": {
                "type": "string",
                "description": "The text or markdown content to write."
            },
            "append": {
                "type": "boolean",
                "description": "Whether to append to the existing file instead of overwriting (default: false)."
            }
        },
        "required": ["relative_path", "content"]
    }
}

DELETE_MEMORY_FILE_TOOL = {
    "name": "delete_memory_file",
    "description": "Delete a file from Ruby's memory folder (requires user confirmation).",
    "input_schema": {
        "type": "object",
        "properties": {
            "relative_path": {
                "type": "string",
                "description": "Relative path inside memory/ of the file to delete."
            }
        },
        "required": ["relative_path"]
    }
}

EXECUTE_SCRIPT_TOOL = {
    "name": "execute_script",
    "description": "Run an approved Python (.py), PowerShell (.ps1), or Batch (.bat) script located in Ruby's scripts/ folder.",
    "input_schema": {
        "type": "object",
        "properties": {
            "script_name": {
                "type": "string",
                "description": "Name of the script to execute (e.g., 'backup.py', 'clean_temp.ps1')."
            },
            "args": {
                "type": "string",
                "description": "Optional arguments to pass to the script."
            }
        },
        "required": ["script_name"]
    }
}
