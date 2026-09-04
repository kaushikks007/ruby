"""
Live microphone test for Ruby's fixed device selection.

Run:
    .\.venv\Scripts\python.exe scripts\mic_live_test.py [seconds]

Streams from whichever mic pick_input_device() chooses and prints live RMS.
Say anything / make noise: you should see RMS jump well above the ~0.000x
digital-silence floor. Red bars = talking, green = quiet.
"""
import sys
import time
from pathlib import Path
import numpy as np
import sounddevice as sd

# Ensure the project root (with the `ruby` package) is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruby.voice.audio_input import pick_input_device, to_mono, MIN_LIVE_RMS

DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0


def main():
    device_idx, channels, rate = pick_input_device(16000)
    if device_idx is None:
        print("No microphone found!")
        return

    print(f"\n>>> Speaking on: device={device_idx} channels={channels} rate={rate}Hz")
    print(">>> Say something / make noise now. Ctrl+C to stop.\n")

    bar_width = 50
    with sd.InputStream(samplerate=rate, channels=channels, device=device_idx,
                        dtype="int16") as stream:
        start = time.time()
        # 50ms blocks
        while time.time() - start < DURATION:
            chunk, _ = stream.read(int(rate * 0.05))
            mono = to_mono(chunk).astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(mono ** 2)))
            loud = rms > 0.03
            level = min(int(rms / 0.2 * bar_width), bar_width)
            bar = "#" * level
            marker = "TALKING" if loud else ("noise" if rms > MIN_LIVE_RMS * 4 else "silent")
            print(f"\r[{marker:7s}] rms={rms:.5f} |{bar:<{bar_width}}|", end="", flush=True)

    print("\n\nDone.")


if __name__ == "__main__":
    main()
