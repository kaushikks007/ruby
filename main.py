"""
Ruby - Personal AI Desktop Assistant
Entry point for launching Ruby.
"""
import sys
import argparse
from pathlib import Path

# Ensure ruby package is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ruby.cli import run_cli
from ruby.voice.voice_selector import run_voice_setup

def main():
    parser = argparse.ArgumentParser(description="Ruby - Personal AI Desktop Assistant")
    parser.add_argument("--voice", action="store_true", help="Launch directly in voice wake-word mode")
    parser.add_argument("--voices", action="store_true", help="Open the interactive voice customizer")
    parser.add_argument("--no-face-confirm", action="store_true",
                        help="Skip owner face confirmation before voice commands (Phase 5)")
    args = parser.parse_args()

    if args.voices:
        run_voice_setup()
    else:
        run_cli(voice_mode=args.voice, face_confirm=not args.no_face_confirm)

if __name__ == "__main__":
    main()
