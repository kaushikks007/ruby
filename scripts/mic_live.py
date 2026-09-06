"""Live mic level test — TALK into the mic while this runs.

Uses the SAME device Ruby's wake-word detector selects (get_cached_device).
If RMS jumps well above ~0.005 while you talk → mic is live (code-threshold fix).
If it stays near ~0.0004 even while talking → mic isn't reaching Windows.

Run from the repo root:
    .venv\\Scripts\\python.exe scripts\\mic_live.py
"""
import sys
import os
import time

sys.path.insert(0, os.getcwd())  # so `from ruby.voice...` resolves when run from repo root

import numpy as np
import sounddevice as sd
from ruby.voice.audio_input import get_cached_device, to_mono

idx, ch, rate = get_cached_device(16000, verbose=True)
print(f"\nTesting device {idx} ({ch}ch @ {rate}Hz) — TALK into the mic now for ~8s...\n")

t0 = time.time()
max_rms = 0.0
with sd.InputStream(samplerate=rate, channels=ch, device=idx, dtype="int16") as s:
    while time.time() - t0 < 8:
        block, _ = s.read(int(rate * 0.2))
        a = to_mono(block).astype(np.float32) / 32768.0
        r = float(np.sqrt(np.mean(a ** 2)))
        max_rms = max(max_rms, r)
        print(f"  {time.time() - t0:4.1f}s  rms={r:.5f}")

print(f"\nPeak RMS while you talked: {max_rms:.5f}")
if max_rms > 0.005:
    print("MIC IS LIVE — carries your voice. Problem = Ruby threshold; I'll fix it in code.")
else:
    print("MIC IS ~SILENT even while talking — NOT a Ruby bug; fix Windows gain/privacy/driver.")