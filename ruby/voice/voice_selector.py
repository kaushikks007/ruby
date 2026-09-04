from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from ruby.voice.tts import TTSEngine, AVAILABLE_VOICES
from ruby.memory_manager import MemoryManager

console = Console()


def run_voice_setup():
    tts = TTSEngine()
    memory_mgr = MemoryManager()
    
    current_choice = tts.get_current_voice_key()
    
    console.print(Panel(
        "[bold magenta]Ruby Voice Selection & Setup[/bold magenta]\n"
        "Preview and choose the voice that feels most natural for Ruby.",
        title="[magenta]Voice Customizer[/magenta]",
        border_style="magenta"
    ))

    table = Table(title="Available Voices", show_header=True, header_style="bold cyan")
    table.add_column("Key", style="yellow")
    table.add_column("Voice Name", style="bold white")
    table.add_column("Style & Gender", style="green")
    table.add_column("Engine", style="dim")
    table.add_column("Status", style="bold magenta")

    for key, info in AVAILABLE_VOICES.items():
        status = "[bold green](Current)[/bold green]" if key == current_choice else ""
        table.add_row(
            key,
            info["name"],
            f"{info['gender']}",
            info["engine"],
            status
        )

    console.print(table)
    console.print("\n[dim]Enter a voice key to preview and select, or 'cancel' to exit:[/dim]")

    while True:
        choice = Prompt.ask("[bold cyan]Choose voice key[/bold cyan]", default=current_choice).strip()
        
        if choice.lower() in ["cancel", "exit", "quit", "q"]:
            console.print("[dim]Voice setup closed without changes.[/dim]")
            break

        if choice in AVAILABLE_VOICES:
            console.print(f"[yellow]Playing sample preview with '{choice}'...[/yellow]")
            preview_text = "Hey kaushik! I'm Ruby, your personal assistant and companion. How's everything going today?"
            tts.speak(preview_text, voice_key=choice, blocking=True)
            
            confirm = Prompt.ask(f"Set [bold green]{choice}[/bold green] as your default Ruby voice? (y/n)", default="y").strip().lower()
            if confirm in ["y", "yes"]:
                tts.set_voice_choice(choice)
                console.print(f"[bold green]✓ Ruby's voice updated to: {AVAILABLE_VOICES[choice]['name']}[/bold green]\n")
                break
            else:
                console.print("[dim]Try another voice key.[/dim]\n")
        else:
            console.print(f"[bold red]Unknown voice key '{choice}'. Please pick from the table above.[/bold red]")


if __name__ == "__main__":
    run_voice_setup()
