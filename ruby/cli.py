import sys
import os

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.theme import Theme

from ruby.brain import RubyBrain
from ruby.memory_manager import MemoryManager
from ruby.tools.web_search import search_web
from ruby.tools.browser_tools import send_whatsapp_message, browse_url, capture_page_screenshot
from ruby.tools.os_tools import launch_app, read_memory_file, write_memory_file, execute_script
from ruby.voice.tts import TTSEngine, clean_text_for_speech
from ruby.voice.voice_selector import run_voice_setup

custom_theme = Theme({
    "ruby": "bold magenta",
    "user": "bold cyan",
    "tool": "italic yellow",
    "system": "dim white",
    "accent": "bold green",
    "warning": "bold red"
})

console = Console(theme=custom_theme)


def print_banner():
    banner_text = """
 [bold magenta]====================================================[/bold magenta]
 [bold magenta]   ____  _   _ ____ __   __                         [/bold magenta]
 [bold magenta]  |  _ \| | | | __ )\ \ / /                         [/bold magenta]
 [bold magenta]  | |_) | | | |  _ \ \ V /   Personal AI Assistant  [/bold magenta]
 [bold magenta]  |  _ <| |_| | |_) | | |    & Desktop Companion    [/bold magenta]
 [bold magenta]  |_| \_\\___/|____/  |_|    Phase 6 — Full Stack   [/bold magenta]
 [bold magenta]====================================================[/bold magenta]
 [dim]  Memory & Data Root: C:\\Users\\sudha\\OneDrive\\ruby  [/dim]
"""
    console.print(banner_text)


def show_help():
    help_md = """
**Ruby Commands:**
- `/open <app>`    - Launch a desktop application (notepad, calc, vscode, chrome, etc.)
- `/read <file>`   - Read a file in Ruby's memory folder
- `/write <f> <c>` - Write content to a file in memory folder
- `/run <script>`  - Run a script in the scripts/ folder
- `/whatsapp <c> <m>` - Send WhatsApp message with confirmation preview
- `/browse <url>`  - Open Chrome and extract page text
- `/screenshot`    - Take screenshot of active browser
- `/voice`         - Start always-listening Voice Loop ("Hey Ruby")
- `/voices`        - Voice Selector & Preview setup
- `/profile`       - View user profile and preferences in memory
- `/memory`        - View recent daily logs and known contacts
- `/projects`      - View active project and hackathon files
- `/search <q>`    - Run a direct live web search
- `/clear`         - Clear current chat context window
- `/exit` / `quit` - Save session summary and exit
"""
    console.print(Panel(Markdown(help_md), title="Ruby Commands", border_style="magenta"))


def run_cli(voice_mode: bool = False, face_confirm: bool = None):
    if voice_mode:
        from ruby.voice.voice_assistant import run_voice
        run_voice(face_confirm=face_confirm, show_avatar=False)
        return

    print_banner()
    
    brain = RubyBrain()
    memory_mgr = brain.memory_mgr
    tts = TTSEngine()
    profile = memory_mgr.load_profile()
    user_name = profile.get("user", {}).get("name", "kaushik")
    voice_key = tts.get_current_voice_key()
    
    console.print(f"[accent]*[/accent] [bold white]Connected to Ruby Brain & OS Control.[/bold white] Welcome back, [bold cyan]{user_name}[/bold cyan]! (Voice: [green]{voice_key}[/green])")
    
    if not brain.api_key:
        console.print(
            Panel(
                "[warning]Note:[/warning] `ANTHROPIC_API_KEY` is not set yet.\n"
                "To enable full reasoning and live chat with Claude, create a `.env` file in `C:\\Users\\sudha\\OneDrive\\ruby\\.env`:\n"
                "[bold cyan]ANTHROPIC_API_KEY=your_anthropic_api_key_here[/bold cyan]\n\n"
                "Local memory, OS app launching, script runner, browser automation, and voice tools are fully functional in the meantime.",
                title="API Key Configuration",
                border_style="yellow"
            )
        )

    console.print("[dim]Type your message or /help for commands. Type /voice for wake-word mode.\n[/dim]")

    session_notes = []

    def on_tool_event(tool_name: str, tool_args: dict):
        if tool_name == "web_search":
            query = tool_args.get("query", "")
            console.print(f"[tool]>> Ruby is checking the web for: \"{query}\"...[/tool]")
        elif tool_name == "fetch_webpage":
            url = tool_args.get("url", "")
            console.print(f"[tool]>> Ruby is reading webpage: {url}...[/tool]")
        elif tool_name == "launch_app":
            app = tool_args.get("app_name", "")
            console.print(f"[tool]>> Ruby is opening: {app}...[/tool]")
        elif tool_name == "execute_script":
            scr = tool_args.get("script_name", "")
            console.print(f"[tool]>> Ruby is executing script: {scr}...[/tool]")
        elif tool_name == "send_whatsapp_message":
            contact = tool_args.get("contact_name", "")
            console.print(f"[tool]>> Ruby is preparing WhatsApp message for: {contact}...[/tool]")
        elif tool_name == "browse_url":
            url = tool_args.get("url", "")
            console.print(f"[tool]>> Ruby is browsing to: {url}...[/tool]")
        elif tool_name == "remember_person":
            name = tool_args.get("name", "")
            console.print(f"[tool]>> Ruby updated memory for: {name}...[/tool]")
        elif tool_name == "save_project_update":
            pname = tool_args.get("project_name", "")
            console.print(f"[tool]>> Ruby updated project notes for: {pname}...[/tool]")
        elif tool_name == "log_daily_event":
            pass  # Log saves silently — no need to notify the user

    while True:
        try:
            user_input = Prompt.ask(f"[user]{user_name}[/user]").strip()
            
            if not user_input:
                continue

            # Command Handling
            cmd_lower = user_input.lower()
            if cmd_lower in ["exit", "quit", "/exit", "/quit"]:
                console.print("\n[ruby]Ruby:[/ruby] Take care! Saving our session notes to your daily log...")
                if session_notes:
                    summary_text = "Session topics discussed:\n" + "\n".join(f"- {note}" for note in session_notes)
                    memory_mgr.save_daily_log(summary_text, tags=["chat-session"])
                    console.print("[accent]✓[/accent] Daily log updated.")
                console.print("[dim]Goodbye![/dim]\n")
                break

            elif cmd_lower == "/help":
                show_help()
                continue

            elif cmd_lower.startswith("/open "):
                app = user_input[6:].strip()
                res = launch_app(app)
                console.print(f"[accent]✓[/accent] {res}")
                continue

            elif cmd_lower.startswith("/read "):
                fpath = user_input[6:].strip()
                res = read_memory_file(fpath)
                console.print(Panel(res, title=f"Memory File: {fpath}", border_style="cyan"))
                continue

            elif cmd_lower.startswith("/write "):
                parts = user_input[7:].strip().split(maxsplit=1)
                if len(parts) == 2:
                    res = write_memory_file(parts[0], parts[1])
                    console.print(f"[accent]✓[/accent] {res}")
                else:
                    console.print("[dim]Usage: /write <relative_file_path> <content>[/dim]")
                continue

            elif cmd_lower.startswith("/run "):
                parts = user_input[5:].strip().split(maxsplit=1)
                sname = parts[0]
                sargs = parts[1] if len(parts) > 1 else None
                res = execute_script(sname, sargs)
                console.print(Panel(res, title=f"Script: {sname}", border_style="green"))
                continue

            elif cmd_lower.startswith("/whatsapp ") or cmd_lower.startswith("/wa "):
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 3:
                    contact = parts[1]
                    msg = parts[2]
                    res = send_whatsapp_message(contact, msg)
                    console.print(f"\n[ruby]Ruby:[/ruby] {res}\n")
                else:
                    console.print("[dim]Usage: /whatsapp <contact_name> <message>[/dim]")
                continue

            elif cmd_lower.startswith("/browse "):
                url = user_input[8:].strip()
                res = browse_url(url)
                console.print(Panel(res, title=f"Browse: {url}", border_style="cyan"))
                continue

            elif cmd_lower == "/screenshot":
                res = capture_page_screenshot()
                console.print(f"[accent]✓[/accent] {res}")
                continue

            elif cmd_lower in ["/voice", "voice"]:
                from ruby.voice.voice_assistant import run_voice
                run_voice(face_confirm=face_confirm)
                continue

            elif cmd_lower in ["/voices", "/setup-voice"]:
                run_voice_setup()
                continue

            elif cmd_lower == "/profile":
                prof = memory_mgr.load_profile()
                import json
                console.print(Panel(json.dumps(prof, indent=2), title="User & Assistant Profile", border_style="cyan"))
                continue

            elif cmd_lower == "/memory":
                logs = memory_mgr.get_recent_daily_logs(days=3)
                if logs:
                    for l in logs:
                        console.print(Panel(l["content"], title=f"Daily Log: {l['date']}", border_style="blue"))
                else:
                    console.print("[dim]No recent daily logs found.[/dim]")
                continue

            elif cmd_lower == "/projects":
                projects = memory_mgr.get_all_projects()
                if projects:
                    for name, content in projects.items():
                        console.print(Panel(content, title=f"Project: {name}", border_style="green"))
                else:
                    console.print("[dim]No active project files found in memory/projects/.[/dim]")
                continue

            elif cmd_lower.startswith("/search "):
                query = user_input[8:].strip()
                console.print(f"[tool]Searching web for: {query}...[/tool]")
                res = search_web(query)
                console.print(Panel(Markdown(res), title=f"Search Results: {query}", border_style="yellow"))
                continue

            elif cmd_lower == "/clear":
                brain.reset_conversation()
                session_notes = []
                console.print("[dim]Conversation history reset for current session.[/dim]")
                continue

            # Record a brief note for session summary
            session_notes.append(user_input[:80])

            # Normal chat
            response = brain.chat(user_input, on_tool_call=on_tool_event)
            console.print(f"\n[ruby]Ruby:[/ruby] {response}\n")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session ended. Exiting...[/dim]")
            break
        except Exception as e:
            console.print(f"\n[warning]Error:[/warning] {str(e)}\n")


if __name__ == "__main__":
    run_cli()
