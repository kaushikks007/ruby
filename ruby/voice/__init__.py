"""
Ruby Voice Subsystem
Local Whisper STT + TTS Engine + 'Hey Ruby' Wake-Word Engine
"""

from ruby.voice.stt import WhisperSTT
from ruby.voice.tts import TTSEngine, AVAILABLE_VOICES
from ruby.voice.wake_word import WakeWordDetector

__all__ = ["WhisperSTT", "TTSEngine", "WakeWordDetector", "AVAILABLE_VOICES"]
