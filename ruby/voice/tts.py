import os
import re
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from ruby.memory_manager import MemoryManager

# High quality voice catalog
AVAILABLE_VOICES = {
    "ruby-warm": {
        "id": "en-US-AriaNeural",
        "name": "Ruby Classic (Warm, Natural, Direct)",
        "engine": "edge-tts",
        "gender": "Female"
    },
    "ruby-conversational": {
        "id": "en-US-JennyNeural",
        "name": "Ruby Upbeat (Conversational, Friendly)",
        "engine": "edge-tts",
        "gender": "Female"
    },
    "ruby-chai": {
        "id": "en-IN-NeerjaNeural",
        "name": "Ruby Chai (Indian English, Warm, Natural)",
        "engine": "edge-tts",
        "gender": "Female"
    },
    "ruby-crisp": {
        "id": "en-GB-SoniaNeural",
        "name": "Ruby Crisp (British, Sharp, Focused)",
        "engine": "edge-tts",
        "gender": "Female"
    },
    "ruby-male": {
        "id": "en-US-GuyNeural",
        "name": "Ruby Deep (Friendly, Masculine)",
        "engine": "edge-tts",
        "gender": "Male"
    },
    "offline-windows": {
        "id": "windows-sapi",
        "name": "Windows Built-in SAPI5 (100% Offline)",
        "engine": "pyttsx3",
        "gender": "System Default"
    }
}


def clean_text_for_speech(text: str) -> str:
    """Removes markdown code blocks, URLs, and formatting tags for smooth TTS."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", " [code omitted] ", text)
    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove markdown links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove markdown headers and bullet markers
    text = re.sub(r"^[#*>-]+\s*", "", text, flags=re.MULTILINE)
    # Remove bold / italic symbols
    text = re.sub(r"[*_~]+", "", text)
    # Remove raw URLs
    text = re.sub(r"https?://\S+", "link", text)
    # Clean excessive whitespace
    text = " ".join(text.split())
    return text.strip()


class TTSEngine:
    def __init__(self):
        self.memory_mgr = MemoryManager()
        self._init_pygame()

    def _init_pygame(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            pass

    def get_current_voice_key(self) -> str:
        profile = self.memory_mgr.load_profile()
        voice_choice = profile.get("assistant", {}).get("voice_choice", "ruby-warm")
        if voice_choice not in AVAILABLE_VOICES:
            voice_choice = "ruby-warm"
        return voice_choice

    def set_voice_choice(self, voice_key: str) -> bool:
        if voice_key not in AVAILABLE_VOICES:
            return False
        return self.memory_mgr.update_profile("assistant", "voice_choice", voice_key)

    async def _speak_edge_tts(self, text: str, voice_id: str, output_path: str):
        import edge_tts
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(output_path)

    def _speak_pyttsx3(self, text: str):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 185)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTSEngine] pyttsx3 error: {e}")

    def speak(self, text: str, voice_key: Optional[str] = None, blocking: bool = True):
        clean_text = clean_text_for_speech(text)
        if not clean_text:
            return

        key = voice_key or self.get_current_voice_key()
        voice_meta = AVAILABLE_VOICES.get(key, AVAILABLE_VOICES["ruby-warm"])
        engine_type = voice_meta.get("engine", "edge-tts")
        voice_id = voice_meta.get("id", "en-US-AriaNeural")

        if engine_type == "pyttsx3":
            self._speak_pyttsx3(clean_text)
            return

        # Use edge-tts with audio playback
        try:
            temp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_path = temp_mp3.name
            temp_mp3.close()

            # Run async edge_tts in event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create new loop for synchronous wrapper
                    import threading
                    def run_async():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        new_loop.run_until_complete(self._speak_edge_tts(clean_text, voice_id, temp_path))
                        new_loop.close()
                    t = threading.Thread(target=run_async)
                    t.start()
                    t.join()
                else:
                    loop.run_until_complete(self._speak_edge_tts(clean_text, voice_id, temp_path))
            except RuntimeError:
                asyncio.run(self._speak_edge_tts(clean_text, voice_id, temp_path))

            # Play audio file
            self._play_audio_file(temp_path, blocking=blocking)

        except Exception as e:
            print(f"[TTSEngine] Edge-TTS failed ({e}), falling back to offline Windows voice...")
            self._speak_pyttsx3(clean_text)

    def _play_audio_file(self, file_path: str, blocking: bool = True):
        try:
            import pygame
            import time
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            if blocking:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
                try:
                    pygame.mixer.music.unload()
                    os.remove(file_path)
                except Exception:
                    pass
        except Exception as e:
            # Fallback: try winsound for wav (convert mp3 -> wav via temp file)
            try:
                import winsound
                winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_NOSTOP)
            except Exception:
                pass
