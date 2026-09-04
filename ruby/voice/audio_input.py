"""
Shared microphone input selection for Ruby's voice subsystem.

Picks the physical microphone that ACTUALLY delivers audio, and avoids Windows
virtual/null capture devices (e.g. "Primary Sound Capture Driver", "Stereo Mix")
which open successfully but return digital silence (RMS ~0.0000). This was the
root cause of the "Hey Ruby" wake word never hearing anything.

The picker probes each candidate live (opens a short stream, measures RMS) and
silently-dropped devices are rejected outright. It also picks a sample rate each
device actually supports (some WASAPI mics refuse 16 kHz and need their native rate).
"""
import time

import numpy as np
import sounddevice as sd

# Device names/substrings that never carry real mic audio on Windows.
# This includes virtual/null capture devices AND any device exposing an output
# path (loopback / "PC Speaker") which would capture the PC's own sound instead
# of a real human voice.
DUMMY_SUBSTRINGS = (
    "primary sound capture driver",
    "stereo mix",
    "monitor of",
    "what u hear",
    "what you hear",
    "pc speaker",
    "2nd output",
    "digital output",
    "speaker (",
    "speakers (",
    "output device",
)
# Names that look like a genuine physical microphone (used as a tiebreak).
GOOD_SUBSTRINGS = (
    "microphone",
    "mic",
    "array",
    "headset",
    "condenser",
    "audio device",
    "input",
)
# Host APIs that are modern, direct device bindings (a real physical input).
# MME and DirectSound are *legacy abstraction layers* that can silently route
# through Windows' default recording device (sometimes "Stereo Mix" / system
# audio) regardless of which physical mic you think you selected.
PREFERRED_HOSTAPIS = ("WASAPI", "WDM-KS", "KS", "MMDevice")

MIN_LIVE_RMS = 0.00005  # below this, treat the device as digitally silent
PROBE_SEC = 0.8


def _rms(x):
    return float(np.sqrt(np.mean(x ** 2)))


def _device_quality(name: str) -> int:
    n = name.lower()
    if any(d in n for d in DUMMY_SUBSTRINGS):
        return -1
    return 1 if any(g in n for g in GOOD_SUBSTRINGS) else 0


def _probe(idx, samplerate, channels, duration=PROBE_SEC):
    """Open a stream and return (rms, error_str). rms is None on open failure."""
    try:
        with sd.InputStream(
            samplerate=samplerate, channels=channels, device=idx, dtype="int16"
        ) as s:
            # Warm-up: read and discard the first buffer. WASAPI / some drivers
            # return stale silence in the first few ms after opening; this avoids
            # false "digital silence" rejects on perfectly good mics.
            warmup_frames = int(samplerate * 1.5)
            s.read(warmup_frames)
            # Now take the real measurement.
            data, _ = s.read(int(samplerate * duration))
        return _rms(data.astype(np.float32) / 32768.0), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def pick_input_device(preferred_rate: int = 16000, verbose: bool = True):
    """Return (device_idx, channels, sample_rate) for a mic with real audio.

    Strategy: prefer a *genuine physical input* bound through a modern host API
    (WASAPI / WDM-KS), matching a real mic by name, rather than blindly trusting
    the OS-default input (which can be a legacy MME alias that silently routes
    system audio). Each candidate is probed live; digitally-silent virtual
    devices are skipped so we never lock onto silence.
    """
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()

    inputs = []
    for idx, dev in enumerate(devices):
        if dev["max_input_channels"] <= 0:
            continue
        host = hostapis[dev["hostapi"]]["name"]
        q = _device_quality(dev["name"])
        if q < 0:
            if verbose:
                print(f"[audio_input] skip {idx}: {dev['name']!r} (virtual/null/loopback device)")
            continue
        inputs.append((idx, dev, host, q))

    def host_priority(host: str) -> int:
        # Modern direct device bindings first; legacy MME/DirectSound last.
        for i, h in enumerate(PREFERRED_HOSTAPIS):
            if h in host:
                return i
        return len(PREFERRED_HOSTAPIS)

    # Order: honest host API first, then physical-mic name match, then by index.
    inputs.sort(key=lambda it: (host_priority(it[2]), -it[3], it[0]))
    if verbose:
        for idx, dev, host, q in inputs:
            print(f"[audio_input] candidate {idx}: {dev['name']!r} (host={host}, q={q})")

    for idx, dev, host, q in inputs:
        native = int(dev["default_samplerate"])
        max_ch = dev["max_input_channels"]
        # Rates to try: preferred (16k), then native, then standard rates.
        rates = list(dict.fromkeys([preferred_rate, native, 48000, 44100, 16000]))
        # IMPORTANT: try FEWER channels before giving up on a device. Multi-channel
        # array mics (e.g. a 4-ch mic where only ch0/1 carry sound) can return
        # silence when 2 channels are requested but real audio at 1 channel.
        channel_opts = list(dict.fromkeys([min(max_ch, 2), 1])) if max_ch >= 1 else [1]
        for rate in rates:
            for channels in channel_opts:
                rms, err = _probe(idx, rate, channels)
                if rms is None:
                    if verbose:
                        print(f"[audio_input] {idx} {dev['name']!r} ch={channels} @{rate}: "
                              f"open failed ({err})")
                    continue
                if rms < MIN_LIVE_RMS:
                    # WASAPI mics sometimes return silence on the first probe
                    # if another app just released the device. Retry once after
                    # a short pause before giving up on this rate/channel combo.
                    if verbose:
                        print(f"[audio_input] {idx} {dev['name']!r} ch={channels} @{rate}: "
                              f"DIGITAL SILENCE rms={rms:.5f} - retrying once...")
                    time.sleep(0.5)
                    rms, err = _probe(idx, rate, channels)
                    if rms is None or rms < MIN_LIVE_RMS:
                        if verbose:
                            print(f"[audio_input] {idx} {dev['name']!r} ch={channels} @{rate}: "
                                  f"retry still silent ({rms}) - continuing")
                        continue
                    # Retry succeeded — fall through to the OK path below
                if verbose:
                    print(f"[audio_input] {idx} {dev['name']!r} ch={channels} @{rate}: "
                          f"live rms={rms:.5f} OK")
                return (idx, channels, rate)

    # Last resort: default input at preferred rate / channel 1.
    default_in = sd.default.device[0] if sd.default.device else None
    if default_in is not None and default_in >= 0:
        chosen = (default_in, 1, preferred_rate)
    elif inputs:
        idx, dev, host, q = inputs[0]
        chosen = (idx, min(dev["max_input_channels"], 2), int(dev["default_samplerate"]))
    else:
        chosen = (None, 1, preferred_rate)
    if verbose:
        print(f"[audio_input] WARNING: no live audio verified, falling back to {chosen}")
    return chosen


# Cache: once we find a working device, remember it so we don't re-probe
# on every wake-word / STT call. The probe cycle opens/closes the mic
# dozens of times and can leave it in a transient state.
_cached_device = None  # (idx, channels, rate) or None


def get_cached_device(preferred_rate: int = 16000, verbose: bool = False):
    """Return a cached (idx, channels, rate).

    On first call, tries the full probe to find a working mic. If the probe
    selects a device but the first real read returns silence (WASAPI warmup
    issue), falls back to the system default input.
    """
    global _cached_device
    if _cached_device is not None:
        return _cached_device

    # Quick path: try system default first (most reliable on Windows)
    default_idx = sd.default.device[0] if sd.default.device else None
    if default_idx is not None and default_idx >= 0:
        dev = sd.query_devices(default_idx)
        if dev["max_input_channels"] > 0:
            rate = int(dev["default_samplerate"])
            ch = min(dev["max_input_channels"], 2)
            # Warmup: read a few seconds to let WASAPI stabilize
            try:
                with sd.InputStream(samplerate=rate, channels=ch,
                                    device=default_idx, dtype='int16') as s:
                    s.read(int(rate * 1.5))
                    data, _ = s.read(int(rate * 0.5))
                rms = float(np.sqrt(np.mean(data.astype(np.float32) / 32768.0) ** 2))
                if rms > MIN_LIVE_RMS:
                    _cached_device = (default_idx, ch, rate)
                    if verbose:
                        print(f"[audio_input] Using default device {default_idx}: "
                              f"{dev['name']!r} ch={ch} @{rate} rms={rms:.5f}")
                    return _cached_device
            except Exception:
                pass

    # Fallback: full probe cycle
    _cached_device = pick_input_device(preferred_rate, verbose=verbose)
    # Give the device a moment to stabilize after the probe cycle
    time.sleep(1.0)
    return _cached_device


def to_mono(chunk):
    """Reduce a (n_frames, n_ch) block to 1-D mono, averaging all channels.

    Averaging (rather than taking only channel[0]) protects against array mics
    where the voice lands on a non-first channel, and against the dead channels
    some multi-channel mics report.
    """
    if chunk.ndim <= 1:
        return chunk
    return chunk.mean(axis=1)
