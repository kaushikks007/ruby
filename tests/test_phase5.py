"""Phase 5 tests: face enrollment + LBPH recognition (synthetic, camera-free).

We inject clearly distinct synthetic "faces" and verify the recognizer separates
them, without needing a real webcam or face. All artifacts go to a temp dir.
"""
import numpy as np
import cv2
import pytest

import ruby.face.enroll as enroll
import ruby.face.recognizer as recognizer
from ruby.face.detector import FaceDetector
from ruby.face.recognizer import FaceRecognizer


def make_face(kind: str) -> np.ndarray:
    """A 100x100 grayscale image that stands in for a face."""
    img = np.full((100, 100), 128, dtype=np.uint8)
    if kind == "alice":
        img[10:40, 10:40] = 255        # bright patch top-left
    elif kind == "bob":
        img[60:90, 60:90] = 15         # dark patch bottom-right
    elif kind == "unknown":
        rng = np.random.default_rng(7)
        img = rng.integers(0, 256, (100, 100), dtype=np.uint8)
    return img


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Point the face storage at a temp dir and clean up after."""
    samples = tmp_path / "samples"
    model = tmp_path / "trained_lbph.yml"
    index = samples / "index.json"
    samples.mkdir(parents=True)
    monkeypatch.setattr(enroll, "SAMPLES_DIR", samples)
    monkeypatch.setattr(recognizer, "SAMPLES_DIR", samples)
    monkeypatch.setattr(recognizer, "MODEL_PATH", model)
    monkeypatch.setattr(recognizer, "INDEX_PATH", index)
    return samples


def test_detector_constructs_and_crops():
    det = FaceDetector()
    gray, rect = det.detect(np.zeros((200, 200, 3), dtype=np.uint8))
    assert rect == []  # no faces in a blank frame
    crop = det.crop_face(np.full((200, 200), 100, dtype=np.uint8), (10, 10, 50, 50))
    assert crop is not None and crop.shape == (100, 100)


def test_enroll_saves_and_counts(isolated):
    enroll.save_sample("alice", make_face("alice"), 0)
    enroll.save_sample("alice", make_face("alice"), 1)
    assert enroll.count_samples("alice") == 2
    assert enroll.count_samples("bob") == 0


def test_train_and_recognize_isolates_labels(isolated):
    # Enroll two distinct identities.
    for i in range(3):
        enroll.save_sample("alice", make_face("alice"), i)
        enroll.save_sample("bob", make_face("bob"), i)

    rec = FaceRecognizer()
    trained = rec.train_from_samples()
    assert trained == 6
    assert recognizer.MODEL_PATH.exists()
    rec2 = FaceRecognizer()
    assert rec2.load() is True

    label, conf = rec2.recognize(make_face("alice"))
    assert label == "alice", f"expected alice, got {label} (conf={conf})"
    label2, _ = rec2.recognize(make_face("bob"))
    assert label2 == "bob"

    # An unknown face should not come back as a confident owner match.
    unknown_label, unknown_conf = rec2.recognize(make_face("unknown"), confidence_threshold=90)
    # The real-match confidence must be far below the unknown one.
    assert unknown_label is None or unknown_conf > conf + 50
