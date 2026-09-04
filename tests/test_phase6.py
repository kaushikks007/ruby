"""Phase 6 tests: avatar state server + overlay assets (no Electron window needed).

Starts the localhost state server on an ephemeral port and verifies the renderer's
polling contract (GET /state) and the Python side's state driver (PUT /state).
Also sanity-checks that the overlay HTML + Electron main exist and reference a local
Three.js build.
"""
import json
import urllib.request
from pathlib import Path

import pytest

from ruby.avatar.bridge import AvatarStateServer, VALID_STATES
from ruby.avatar import bridge

AVATAR_DIR = Path(__file__).resolve().parent.parent / "ruby" / "avatar"


def _req(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_server_starts_and_initial_state_is_idle():
    s = AvatarStateServer(port=0)
    s.start()
    try:
        port = s.server.server_address[1]
        status, body = _req("GET", f"http://127.0.0.1:{port}/state")
        assert status == 200
        assert body["state"] == "idle"
    finally:
        s.stop()


def test_set_state_and_get_roundtrip():
    s = AvatarStateServer(port=0)
    s.start()
    try:
        port = s.server.server_address[1]
        status, body = _req("PUT", f"http://127.0.0.1:{port}/state", {"state": "speaking"})
        assert status == 200 and body["state"] == "speaking"
        _, body = _req("GET", f"http://127.0.0.1:{port}/state")
        assert body["state"] == "speaking"

        # Invalid states rejected.
        status, _ = _req("PUT", f"http://127.0.0.1:{port}/state", {"state": "dancing"})
        assert status == 400
    finally:
        s.stop()


def test_valid_states_are_the_three_the_avatar_reacts_to():
    assert VALID_STATES == {"idle", "listening", "speaking"}


def test_overlay_assets_are_local():
    assert (AVATAR_DIR / "avatar.html").exists()
    assert (AVATAR_DIR / "main.js").exists()
    assert (AVATAR_DIR / "package.json").exists()
    # The HTML must load a local Three.js build (offline-capable), not depend on CDN.
    html = (AVATAR_DIR / "avatar.html").read_text(encoding="utf-8")
    assert 'src="three.min.js"' in html
    three_build = AVATAR_DIR / "three.min.js"
    assert three_build.exists() and three_build.stat().st_size > 100_000
