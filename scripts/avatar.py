"""
Launch Ruby's 3D avatar overlay (Phase 6) standalone.

Run:
    .\.venv\Scripts\python.exe scripts\avatar.py            # window + server, idle
    .\.venv\Scripts\python.exe scripts\avatar.py --state listening
    .\.venv\Scripts\python.exe scripts\avatar.py --server-only   # no Electron window

While it runs you can type idle|listening|speaking to change the animation live.
Press Ctrl+C to stop.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruby.avatar.bridge import AvatarStateServer, launch_electron


def main():
    args = sys.argv[1:]
    initial = "idle"
    server_only = False
    if args and args[0] == "--server-only":
        server_only = True
    if "--state" in args:
        i = args.index("--state")
        if i + 1 < len(args):
            initial = args[i + 1]

    server = AvatarStateServer()
    server.start()
    if not server_only:
        if launch_electron():
            print("Ruby avatar window opened (drag top edge to move, spider to orbit).")
        else:
            print("Electron not found - running server-only (no window).")
    print(f"Avatar state server on 127.0.0.1:{server.port}  (state={initial})")
    server.set_state(initial)

    try:
        while True:
            cmd = input("avatar state [idle/listening/speaking, or quit]: ").strip().lower()
            if cmd in ("quit", "exit", "q"):
                break
            if cmd in ("idle", "listening", "speaking"):
                server.set_state(cmd)
                print(f"  -> {cmd}")
            elif cmd:
                print("  valid states: idle | listening | speaking")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        server.stop()
    print("Stopped.")


if __name__ == "__main__":
    main()
