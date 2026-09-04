import os
import sys
import wave
import tempfile
import numpy as np
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ruby.voice.tts import TTSEngine, clean_text_for_speech, AVAILABLE_VOICES
from ruby.voice.stt import WhisperSTT
from ruby.voice.wake_word import WakeWordDetector
from ruby.memory_manager import MemoryManager


def test_voice_catalog():
    assert len(AVAILABLE_VOICES) >= 4
    assert "ruby-warm" in AVAILABLE_VOICES
    assert AVAILABLE_VOICES["ruby-warm"]["id"] == "en-US-AriaNeural"
    assert "offline-windows" in AVAILABLE_VOICES


def test_clean_text_for_speech():
    markdown_text = """
# Hello kaushik!
Check out this `code_block` and [Google](https://google.com).
```python
def test():
    pass
```
* Important note: **Ruby** is online!
"""
    cleaned = clean_text_for_speech(markdown_text)
    assert "#" not in cleaned
    assert "```" not in cleaned
    assert "https://" not in cleaned
    assert "**" not in cleaned
    assert "Ruby is online!" in cleaned


def test_tts_voice_switch_and_memory():
    tts = TTSEngine()
    mm = MemoryManager()
    
    # Set to a specific voice
    success = tts.set_voice_choice("ruby-conversational")
    assert success is True
    assert tts.get_current_voice_key() == "ruby-conversational"
    
    profile = mm.load_profile()
    assert profile["assistant"]["voice_choice"] == "ruby-conversational"
    
    # Reset back to default
    tts.set_voice_choice("ruby-warm")
    assert tts.get_current_voice_key() == "ruby-warm"


def test_wake_word_detector_init():
    detector = WakeWordDetector(wake_word="hey ruby")
    assert detector.wake_word == "hey ruby"
    assert detector.sensitivity == 0.5


def test_whisper_stt_transcription():
    # Create a small synthetic wav file (1 second of silence/sine tone) to test model inference
    sample_rate = 16000
    duration = 1.0  # 1 second
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = (np.sin(2 * np.pi * 440 * t) * 0.1).astype(np.float32)

    stt = WhisperSTT(model_size="tiny.en")
    assert stt.model is not None

    # Test numpy array transcription
    result = stt.transcribe_numpy(audio_data, sample_rate=sample_rate)
    assert isinstance(result, str)
