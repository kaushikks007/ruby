"""List all audio input devices and their default settings."""
import sounddevice as sd

print(sd.query_devices())
print("DEFAULT:", sd.default.device)
