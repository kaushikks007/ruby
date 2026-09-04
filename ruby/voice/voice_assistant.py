import sys
import time
from rich.console import Console
from rich.panel import Panel

from ruby.brain import RubyBrain
from ruby.voice.stt import WhisperSTT
from ruby.voice.tts import TTSEngine
from ruby.voice.wake_word import WakeWordDetector
from ruby.memory_manager import MemoryManager

try:
    from ruby.face.face_guard import FaceGuard
except Exception:
    FaceGuard = None

try:
    from ruby.avatar.bridge import AvatarStateServer, launch_electron
except Exception:
    AvatarStateServer = None
    launch_electron = None

console = Console()


class RubyVoiceAssistant:
    def __init__(self, model_size: str = "base.en", confirm_face: bool = None, show_avatar: bool = None):
        # Force a fresh mic probe — the cached device from a prior session can
        # go stale and return digital silence, making the wake word deaf.
        import ruby.voice.audio_input as _ai
        _ai._cached_device = None

        self.brain = RubyBrain()
        self.memory_mgr = MemoryManager()
        self.stt = WhisperSTT(model_size=model_size)
        self.tts = TTSEngine()
        self.wake_detector = WakeWordDetector()
        # Default confirmation from config/env unless explicitly overridden.
        if confirm_face is None:
            from ruby.config import FACE_CONFIRM_VOICE
            confirm_face = FACE_CONFIRM_VOICE
        self.face_guard = FaceGuard() if (confirm_face and FaceGuard is not None) else None
        self.confirm_face = confirm_face and FaceGuard is not None
        self.is_running = False
        # Avatar: default off unless RUBY_AVATAR=1 or show_avatar=True
        if show_avatar is None:
            import os
            show_avatar = os.getenv("RUBY_AVATAR", "0").lower() not in ("0", "false", "no")
        self.avatar = self._init_avatar() if show_avatar else None

    def _init_avatar(self):
        """Start the avatar state server + overlay window (best-effort, optional)."""
        if AvatarStateServer is None:
            return None
        try:
            server = AvatarStateServer()
            server.start()
            # Only show the window if Electron is actually installed.
            if launch_electron:
                try:
                    launch_electron()
                except Exception as e:
                    print(f"[avatar] window launch failed (voice continues): {e}")
            return server
        except Exception as e:
            print(f"[avatar] disabled (voice continues): {e}")
            return None

    def _avatar_state(self, state: str):
        if self.avatar is not None:
            try:
                self.avatar.set_state(state)
            except Exception:
                pass

    def start(self):
        self.is_running = True
        user_name = self.memory_mgr.load_profile().get("user", {}).get("name", "kaushik")
        voice_info = self.tts.get_current_voice_key()
        
        console.print(Panel(
            f"[bold magenta]Ruby Voice Assistant Active[/bold magenta]\n"
            f"[bold white]Wake word:[/bold white] [bold cyan]\"Hey Ruby\"[/bold cyan]\n"
            f"[bold white]Active Voice:[/bold white] [bold green]{voice_info}[/bold green]\n"
            f"[bold white]Owner:[/bold white] [bold yellow]{user_name}[/bold yellow]\n\n"
            f"[dim]Say 'Hey Ruby' to wake her up, or press Ctrl+C to return to terminal.[/dim]",
            title="[magenta]Voice Loop[/magenta]",
            border_style="magenta"
        ))

        while self.is_running:
            try:
                console.print("\n[dim]👂 Listening for 'Hey Ruby'...[/dim]")
                
                # Listen for wake word
                wake_triggered = self.wake_detector.listen_for_wake_word(
                    stop_check=lambda: not self.is_running
                )

                if not wake_triggered:
                    continue

                console.print("\n[bold magenta]⚡ 'Hey Ruby' detected![/bold magenta]")
                # Short spoken or tone acknowledgment
                self._avatar_state("speaking")
                self.tts.speak("I'm listening", blocking=True)

                # Phase 5: confirm it's really the owner before acting on any command.
                if self.confirm_face:
                    console.print("[bold cyan]📷 Checking it's you...[/bold cyan]")
                    verdict = self.face_guard.confirm_user(required_frames=4, timeout_seconds=10)
                    if not verdict["matched"]:
                        console.print("[bold yellow]Face not recognized - skipping command.[/bold yellow]")
                        self._avatar_state("speaking")
                        if verdict.get("frames", 0) == 0 and not verdict.get("label"):
                            self.tts.speak("I didn't recognize you. Let me keep listening for 'Hey Ruby'.")
                        else:
                            self.tts.speak("That doesn't look like you. I'll hold off on that.")
                        self._avatar_state("idle")
                        continue

                self._avatar_state("listening")
                console.print("[bold cyan]🎤 Listening for your command...[/bold cyan]")
                _, user_speech = self.stt.record_until_silence(
                    silence_duration=1.5,
                    max_duration=25.0
                )

                if not user_speech:
                    console.print("[dim]Didn't catch that. Returning to standby.[/dim]")
                    self._avatar_state("idle")
                    continue

                console.print(f"[bold cyan]{user_name}:[/bold cyan] {user_speech}")

                def on_tool(name, args):
                    if name == "web_search":
                        console.print(f"[italic yellow]⚡ Checking web for: {args.get('query')}[/italic yellow]")

                # Brain reasoning (voice mode keeps responses short)
                response = self.brain.chat(user_speech, on_tool_call=on_tool, voice_mode=True)
                console.print(f"[bold magenta]Ruby:[/bold magenta] {response}\n")

                # Speak response (avatar shows "speaking" while talking)
                self._avatar_state("speaking")
                self.tts.speak(response, blocking=True)
                self._avatar_state("idle")

            except KeyboardInterrupt:
                console.print("\n[dim]Voice loop stopped by user.[/dim]")
                self.is_running = False
                break
            except Exception as e:
                console.print(f"[bold red]Voice loop error:[/bold red] {e}")
                time.sleep(1)


def run_voice(face_confirm: bool = None, show_avatar: bool = None):
    assistant = RubyVoiceAssistant(confirm_face=face_confirm, show_avatar=show_avatar)
    assistant.start()


if __name__ == "__main__":
    run_voice()
