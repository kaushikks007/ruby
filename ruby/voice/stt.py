import io
import time
import wave
import tempfile
import numpy as np
from pathlib import Path
from typing import Optional, Union, Tuple

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

from ruby.voice.audio_input import get_cached_device, to_mono


class WhisperSTT:
    def __init__(self, model_size: str = "base.en", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    @property
    def model(self):
        if self._model is None:
            if WhisperModel is None:
                raise ImportError("faster-whisper is not installed.")
            print(f"[WhisperSTT] Loading local Whisper model '{self.model_size}'...")
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            print("[WhisperSTT] Model loaded successfully.")
        return self._model

    def transcribe_file(self, audio_file_path: Union[str, Path]) -> str:
        """Transcribes an existing audio file (.wav, .mp3, etc.)."""
        segments, info = self.model.transcribe(str(audio_file_path), beam_size=5)
        text_parts = [segment.text.strip() for segment in segments]
        return " ".join(text_parts).strip()

    def transcribe_numpy(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribes a 1D float32 or int16 numpy audio array.

        Whisper expects 16kHz audio. Some mics only open at their native rate
        (e.g. 48kHz), so we resample down to 16kHz first when needed to keep
        recognition accurate.
        """
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        audio_data = audio_data.flatten()
        if sample_rate != 16000 and audio_data.size:
            try:
                from scipy import signal
                audio_data = signal.resample_poly(
                    audio_data, 16000, sample_rate
                ).astype(np.float32)
                sample_rate = 16000
            except Exception as e:
                print(f"[WhisperSTT] resample skipped ({e}); using raw {sample_rate}Hz input")
        # Boost quiet microphone input. Whisper transcribes best on normalized
        # audio; very-low-level signals (array mics / low gain) return silence
        # or garbage otherwise. We only scale genuinely-quiet-but-audible audio,
        # never near-silence (which would just amplify noise) or already-loud audio.
        if audio_data.size:
            peak = float(np.max(np.abs(audio_data)))
            if 0.002 < peak < 0.15:
                audio_data = (audio_data * (0.35 / peak)).astype(np.float32)
        segments, info = self.model.transcribe(audio_data, beam_size=5)
        text_parts = [segment.text.strip() for segment in segments]
        return " ".join(text_parts).strip()

    def record_until_silence(
        self,
        sample_rate: int = 16000,
        silence_threshold: float = 0.001,
        silence_duration: float = 1.5,
        max_duration: float = 30.0,
        on_start_speech=None
    ) -> Tuple[np.ndarray, str]:
        """
        Records audio from microphone until user finishes speaking (silence detected),
        then transcribes using local Whisper.
        """
        if sd is None:
            raise ImportError("sounddevice is not installed.")

        device_idx, channels, actual_rate = get_cached_device(sample_rate)
        if device_idx is None:
            print("[WhisperSTT] No microphone found.")
            return np.array([]), ""
        if actual_rate != sample_rate:
            print(f"[WhisperSTT] Using device {device_idx} at native rate {actual_rate}Hz "
                  f"(requested {sample_rate}Hz).")
        chunk_size = int(actual_rate * 0.1) # 100ms chunks
        audio_chunks = []

        has_started_speaking = False
        silence_start_time = None
        start_time = time.time()

        print("[WhisperSTT] Listening...")
        with sd.InputStream(samplerate=actual_rate, channels=channels, device=device_idx, dtype='float32') as stream:
            while True:
                chunk, _ = stream.read(chunk_size)

                # Downmix to mono, averaging channels (protects against array mics).
                chunk_mono = to_mono(chunk)

                audio_chunks.append(chunk_mono)
                
                # Calculate RMS energy
                rms = np.sqrt(np.mean(chunk_mono**2))
                
                if rms > silence_threshold:
                    if not has_started_speaking:
                        has_started_speaking = True
                        if on_start_speech:
                            on_start_speech()
                    silence_start_time = None
                else:
                    if has_started_speaking:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time >= silence_duration:
                            # User stopped speaking
                            break
                            
                # Timeout safety
                if time.time() - start_time >= max_duration:
                    break
                    
                # If no speech started within 8 seconds, timeout
                if not has_started_speaking and (time.time() - start_time >= 8.0):
                    return np.array([]), ""

        if not audio_chunks or not has_started_speaking:
            return np.array([]), ""

        full_audio = np.concatenate(audio_chunks, axis=0).flatten()
        transcription = self.transcribe_numpy(full_audio, sample_rate=actual_rate)
        return full_audio, transcription
