"""
Mic diagnostic - measure real RMS from EVERY input device to find which
one actually delivers audio (vs digital silence from virtual/null devices).
Run:
    .\.venv\Scripts\python.exe scripts\mic_diag.py
No talking needed - a working physical mic picks up at least ambient/floor
noise, so RMS should be well above the ~0.000x "digital silence" level.
"""
import sys
import time
import numpy as np
import sounddevice as sd


def rms(x):
    return float(np.sqrt(np.mean(x ** 2)))


def probe_device(idx, dev, samplerate, channels, duration=1.5):
    """Open a stream and measure RMS. Returns (rms, error)."""
    try:
        with sd.InputStream(
            samplerate=samplerate, channels=channels, device=idx, dtype="int16"
        ) as stream:
            time.sleep(0.3)  # let the device settle
            frames = int(samplerate * duration)
            data, _ = stream.read(frames)
        audio = data.astype(np.float32) / 32768.0
        per_ch = [rms(audio[:, c]) for c in range(channels)]
        return (rms(audio.flatten()), max(per_ch), per_ch), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def main():
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    defaults = sd.default.device
    print("=" * 70)
    print("DEFAULT DEVICE:  input idx =", defaults[0], "| output idx =", defaults[1])
    print("=" * 70)

    input_devices = []
    for idx, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            input_devices.append((idx, dev))

    rows = []
    for idx, dev in input_devices:
        name = dev["name"]
        host = hostapis[dev["hostapi"]]["name"]
        max_ch = dev["max_input_channels"]
        default_sr = int(dev["default_samplerate"])

        native_ok = False
        # Probe at native rate, using ALL available input channels
        for ch in (max_ch, min(max_ch, 2), 1):
            res, err = probe_device(idx, dev, default_sr, ch, duration=1.2)
            if res is not None:
                total, peak, per_ch = res
                print(f"[{idx}] {name!r}  | {host} | ch={max_ch} default_sr={default_sr}")
                print(f"      probe ch={ch} @{default_sr}Hz  overall_rms={total:.5f} "
                      f"peak_rms={peak:.5f}  per_ch={[f'{p:.5f}' for p in per_ch]}")
                if total > 0.001 or peak > 0.001:
                    native_ok = True
                    rows.append((total, idx, name, ch, default_sr))
                break  # first channel config that opens is enough to gauge
            else:
                print(f"[{idx}] {name!r}  | probe ch={ch} @{default_sr}Hz FAILED: {err}")

        # Probe at 16kHz with 1 channel (what the wake-word code effectively uses)
        if max_ch >= 1:
            res, err = probe_device(idx, dev, 16000, 1, duration=1.2)
            if res is not None:
                total, peak, per_ch = res
                print(f"      probe ch=1 @16000Hz  overall_rms={total:.5f} peak_rms={peak:.5f}")
                if native_ok is False and total > 0.001:
                    rows.append((total, idx, name, 1, 16000))
            else:
                print(f"      probe ch=1 @16000Hz FAILED: {err}")

    print("=" * 70)
    if rows:
        rows.sort(reverse=True)
        print("Devices with real audio (highest RMS first) - RECOMMEND:"
              if any(r[0] > 0.001 for r in rows) else "Best-of-a-bad-bunch:")
        for total, idx, name, ch, sr in rows[:5]:
            print(f"  [{idx}] {name!r}  ch={ch} @{sr}Hz  rms={total:.5f}")
    else:
        print("NO device produced real audio (all digital silence). "
              "Check mic hardware/Windows privacy/volume/enhancements.")


if __name__ == "__main__":
    main()
