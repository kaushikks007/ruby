import time
import numpy as np
from typing import Callable, Optional
try:
    import sounddevice as sd
except ImportError:
    sd = None
from ruby.voice.audio_input import get_cached_device, to_mono
try:
    import openwakeword
    from openwakeword.model import Model as OWWModel
except Exception:
    OWWModel = None
class WakeWordDetector:
    """
    Detects the 'Hey Ruby' wake word from microphone stream.
    Supports openWakeWord engine with fast local audio energy & Whisper verification fallback.
    """
    def __init__(self, wake_word: str = "hey ruby", sensitivity: float = 0.5):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self.oww_model = None
        self._stt = None  # local Whisper, lazy-loaded once and reused
        # openwakeword requires tflite-runtime (unavailable on Windows) or
        # ONNX-converted models. Skip it and use the reliable Whisper fallback.
        # self._init_oww()

    def _transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        """Lazily load one Whisper model and transcribe the utterance (lowercased).

        Uses base.en for accurate wake-word detection (tiny.en hallucinates
        too often on short phrases like 'Hey Ruby').
        """
        if self._stt is None:
            from ruby.voice.stt import WhisperSTT
            print("[WakeWordDetector] Loading Whisper for wake-word verification...")
            self._stt = WhisperSTT(model_size="base.en")
        try:
            return self._stt.transcribe_numpy(audio, sample_rate=sample_rate).lower()
        except Exception as e:
            print(f"[WakeWordDetector] STT check failed: {e}")
            return ""

    def _is_wake_phrase(self, audio: np.ndarray, sample_rate: int) -> bool:
        """True if the transcribed utterance contains the wake word."""
        text = self._transcribe(audio, sample_rate)
        if not text:
            return False
        # Direct match: 'hey ruby', 'ruby', 'hi ruby', etc.
        if "ruby" in text or self.wake_word in text:
            return True
        # Fuzzy match: Whisper may mishear 'ruby' as similar words
        # (e.g. 'rookie', 'ruby', 'rueby', 'ruben', etc.)
        fuzzy_matches = ["rueby", "rookie", "ruben", "rubi", "ruba", "rhuby"]
        return any(w in text for w in fuzzy_matches)
    def _init_oww(self):
        if OWWModel is not None:
            try:
                # Initialize openwakeword model
                self.oww_model = OWWModel(inference_framework="onnx")
            except Exception as e:
                # print(f"[WakeWordDetector] openwakeword fallback: {e}")
                self.oww_model = None
    def listen_for_wake_word(
        self,
        sample_rate: int = 16000,
        energy_threshold: float = 0.0006,
        end_speech_silence: float = 0.4,
        max_speech_seconds: float = 3.0,
        on_listening_heartbeat: Optional[Callable] = None,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Blocks and listens to microphone until wake word is triggered or stop_check() returns True.

        Utterance handling: speech is accumulated into a buffer. Instead of wiping the
        buffer on every micro-dip in energy (which silently dropped short phrases like
        "Hey Ruby"), the phrase is kept until ~end_speech_silence seconds of trailing
        silence, then transcribed once. Requires enough non-silent audio in total
        (queries every ~max_speech_seconds of continuous speech as a safety net).
        """
        if sd is None:
            raise ImportError("sounddevice is not installed.")

        device_idx, channels, actual_rate = get_cached_device(sample_rate)
        if device_idx is None:
            print("[WakeWordDetector] No microphone found.")
            return False
        if actual_rate != sample_rate:
            print(f"[WakeWordDetector] Using device {device_idx} at native rate "
                  f"{actual_rate}Hz (requested {sample_rate}Hz).")
        chunk_size = int(actual_rate * 0.08)  # 80ms chunk (openwakeword standard)
        min_speech_chunks = max(4, int(0.5 / 0.08))   # ~0.5s before we treat it as a phrase
        safety_chunks = int(max_speech_seconds / 0.08)
        window_chunks = int(1.6 / 0.08)               # trailing window for the ramble safety net
        speech_buffer = []
        silence_start = None
        last_heartbeat = time.time()
        # Adaptive noise floor. We refine a rolling estimate from genuinely quiet
        # frames so persistent ambient/media noise can't flood the detector and
        # make it "hear speech" constantly. Speech is judged against a multiple of
        # this floor (bounded below by energy_threshold).
        noise_est = float(energy_threshold)
        NOISE_MARGIN = 2.5

        with sd.InputStream(samplerate=actual_rate, channels=channels,
                            device=device_idx, dtype='int16') as stream:
            while True:
                if stop_check and stop_check():
                    return False
                chunk, _ = stream.read(chunk_size)

                # Downmix to mono, averaging channels (protects against array mics).
                audio_np = to_mono(chunk).astype(np.int16)

                # Check with openwakeword if loaded (fast path; usually unavailable here).
                if self.oww_model is not None:
                    self.oww_model.predict(audio_np)
                    for model_name, scores in self.oww_model.prediction_buffer.items():
                        if scores and scores[-1] > self.sensitivity:
                            return True

                audio_float = audio_np.astype(np.float32) / 32768.0
                rms = np.sqrt(np.mean(audio_float ** 2))
                threshold = max(energy_threshold, noise_est * NOISE_MARGIN)

                if rms > threshold:
                    speech_buffer.append(audio_float)
                    silence_start = None
                    # Safety net: continuous talking (no natural pause) — check the
                    # trailing window periodically, then reset for a fresh shot.
                    if len(speech_buffer) >= safety_chunks:
                        if self._is_wake_phrase(
                                np.concatenate(speech_buffer[-window_chunks:]), actual_rate):
                            return True
                        speech_buffer = []
                        silence_start = None
                else:
                    # A genuinely quiet frame: gently track the noise floor.
                    noise_est = 0.95 * noise_est + 0.05 * rms
                    if speech_buffer:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start >= end_speech_silence:
                            # Phrase finished. Transcribe once and decide.
                            if len(speech_buffer) >= min_speech_chunks and \
                                    self._is_wake_phrase(
                                        np.concatenate(speech_buffer), actual_rate):
                                return True
                            speech_buffer = []
                            silence_start = None

                if on_listening_heartbeat and (time.time() - last_heartbeat > 2.0):
                    on_listening_heartbeat()
                    last_heartbeat = time.time()