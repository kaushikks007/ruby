"""Python <-> Electron bridge for Ruby's 3D avatar overlay (Phase 6).

Two halves:
  1. A tiny localhost HTTP server (stdlib) that holds the avatar's current state
     ("idle" | "listening" | "speaking"). The Electron renderer polls
     http://127.0.0.1:<port>/state and animates accordingly. Nothing leaves the PC.
  2. launch_electron() starts the always-on-top transparent overlay window.

The avatar is optional: if Electron can't start, the voice loop just runs without
a visual, so failures here are always non-fatal.
"""
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DEFAULT_STATE_PORT = 47652
VALID_STATES = {"idle", "listening", "speaking"}
AVATAR_DIR = Path(__file__).resolve().parent


class _StateHandler(BaseHTTPRequestHandler):
    # Shared state hangs off the server instance (self.server.ruby_state).
    def _send(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if path in ("/state", "/state/"):
            self._send(200, {"state": self.server.ruby_state.get("state", "idle")})
        else:
            self._send(404, {"error": "not found"})

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}
        state = str(payload.get("state", "idle")).strip().lower()
        if state not in VALID_STATES:
            self._send(400, {"error": f"invalid state; choose from {sorted(VALID_STATES)}"})
            return
        with self.server._lock:
            self.server.ruby_state["state"] = state
        self._send(200, {"state": state})

    def log_message(self, *args):
        pass


class AvatarStateServer:
    """Threaded localhost server that the avatar renderer polls for its state."""

    def __init__(self, port: int = DEFAULT_STATE_PORT):
        self.port = port
        self.state = {"state": "idle"}
        self._lock = threading.Lock()
        self.server = None
        self.thread = None

    def start(self):
        if self.server is not None:
            return self
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), _StateHandler)
        self.server.ruby_state = self.state  # shared mutable dict for handlers
        self.server._lock = self._lock  # shared lock for thread-safe state updates
        ready = threading.Event()
        def _serve():
            ready.set()
            self.server.serve_forever()
        self.thread = threading.Thread(target=_serve, daemon=True)
        self.thread.start()
        ready.wait(timeout=3)  # block until the server is actually listening
        return self

    def set_state(self, state: str):
        if state in VALID_STATES:
            with self._lock:
                self.state["state"] = state

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
        return False


def launch_electron(avatar_dir: Path = AVATAR_DIR):
    """Start the overlay window. Best-effort; returns True if spawned a process."""
    electron = avatar_dir / "node_modules" / "electron" / "dist" / "electron.exe"
    if not electron.exists():
        return False
    subprocess.Popen(
        [str(electron), str(avatar_dir)],
        cwd=str(avatar_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True
