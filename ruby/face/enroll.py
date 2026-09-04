"""Face enrollment: capture the owner's face samples so the recognizer can learn them.

Samples are stored as grayscale PNG crops under
memory/face_embeddings/samples/<label>/ and used to train an LBPH model. All local.
"""
from pathlib import Path

import cv2

from ruby.config import FACE_EMBEDDINGS_DIR
from ruby.face.camera import Camera
from ruby.face.detector import FaceDetector

SAMPLES_DIR = FACE_EMBEDDINGS_DIR / "samples"
SAMPLE_SIZE = (100, 100)


def save_sample(label: str, gray_face, count: int) -> Path:
    """Persist one grayscale face crop for `label`. Returns the file path."""
    label_dir = SAMPLES_DIR / label
    label_dir.mkdir(parents=True, exist_ok=True)
    path = label_dir / f"{count:03d}.png"
    cv2.imwrite(str(path), gray_face)
    return path


def count_samples(label: str) -> int:
    label_dir = SAMPLES_DIR / label
    if not label_dir.is_dir():
        return 0
    return len(list(label_dir.glob("*.png")))


def enroll_from_camera(label: str, n_samples: int = 20, preview: bool = False) -> int:
    """Capture `n_samples` face crops of `label` from the webcam and save them.

    Opens a small preview window; press 's' to capture one sample at a time,
    or it auto-collects on detection. Returns how many samples were saved.
    """
    detector = FaceDetector()
    saved = 0
    with Camera() as cam:
        if not cam.read()[0]:
            raise RuntimeError("Could not open the webcam. Check camera permissions.")
        print(f"[face/enroll] Capturing {label}... look at the camera.")
        print("[face/enroll] Press 's' to save a sample, 'q' to quit.", flush=True)
        while saved < n_samples:
            ok, frame = cam.read()
            if not ok:
                continue
            gray, rect = detector.largest_face(frame)
            if rect:
                x, y, w, h = rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            if preview:
                cv2.imshow("Enroll - Ruby", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("s") and rect:
                    crop = detector.crop_face(gray, rect, SAMPLE_SIZE)
                    if crop is not None:
                        save_sample(label, crop, saved)
                        saved += 1
                        print(f"  saved {saved}/{n_samples}", end="\r", flush=True)
            elif rect:
                crop = detector.crop_face(gray, rect, SAMPLE_SIZE)
                if crop is not None:
                    save_sample(label, crop, saved)
                    saved += 1
                    print(f"  saved {saved}/{n_samples}", end="\r", flush=True)
    if preview:
        cv2.destroyAllWindows()
    print()
    print(f"[face/enroll] Done: {saved} sample(s) saved for '{label}'.")
    return saved


def label_dir(label: str) -> Path:
    return SAMPLES_DIR / label


def all_labels() -> list:
    if not SAMPLES_DIR.is_dir():
        return []
    return sorted(d.name for d in SAMPLES_DIR.iterdir() if d.is_dir())
