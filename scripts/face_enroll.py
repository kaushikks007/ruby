"""
Enroll the owner's face for Ruby (Phase 5).

Run:
    .\.venv\Scripts\python.exe scripts\face_enroll.py [label] [n_samples]

Opens a preview window. Press 's' to save the current detected face, 'q' to stop.
Default label is the owner name from memory/profile.json (fallback 'sudha').
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruby.config import PROFILE_PATH
from ruby.face.enroll import enroll_from_camera, count_samples


def main():
    label = None
    n = 20
    if len(sys.argv) > 1:
        label = sys.argv[1]
    if len(sys.argv) > 2:
        n = int(sys.argv[2])

    if not label:
        try:
            with open(PROFILE_PATH, encoding="utf-8") as f:
                label = json.load(f).get("user", {}).get("name", "sudha")
        except Exception:
            label = "sudha"
        label = str(label).lower().replace(" ", "_")

    print(f"Enrolling face for label: {label!r}  (existing samples: {count_samples(label)})")
    enroll_from_camera(label, n_samples=n, preview=True)


if __name__ == "__main__":
    main()
