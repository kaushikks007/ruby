"""One-shot: point face enrollment at the correct owner label.

Removes any samples collected under the wrong label and captures fresh ones
under the intended label. Run:
    .venv\\Scripts\\python.exe scripts\\re_enroll_face.py <label>
(e.g.  scripts\\re_enroll_face.py kaushik)
"""
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ruby.config import PROFILE_PATH
from ruby.face.enroll import enroll_from_camera, SAMPLES_DIR, count_samples


def main():
    label = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower().replace(" ", "_")
    if not label:
        import json
        try:
            with open(PROFILE_PATH, encoding="utf-8") as f:
                label = json.load(f).get("user", {}).get("name", "sudha").lower().replace(" ", "_")
        except Exception:
            label = "sudha"

    print(f"Target label: {label!r}")

    # Drop any other enrolled labels so there's exactly one owner.
    if SAMPLES_DIR.is_dir():
        for d in SAMPLES_DIR.iterdir():
            if d.is_dir() and d.name != label:
                print(f"Removing stale '{d.name}' samples...")
                shutil.rmtree(d)

    current = count_samples(label)
    print(f"Existing samples for '{label}': {current}")
    if current == 0:
        n = enroll_from_camera(label, n_samples=20, preview=False)
        print(f"Captured {n} fresh samples.")
    else:
        print("Already enrolled; skipping capture.")

    # Rebuild the recognizer from disk so labels are consistent.
    from ruby.face.recognizer import FaceRecognizer
    rec = FaceRecognizer()
    trained = rec.train_from_samples()
    print(f"Trained on {trained} samples. Labels: {rec.id_of}")


if __name__ == "__main__":
    main()