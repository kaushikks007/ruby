"""LBPH face recognizer trained from enrolled samples. All local (OpenCV).

Samples live in memory/face_embeddings/samples/<label>/*.png and the trained model
is saved to memory/face_embeddings/trained_lbph.yml. For LBPH, lower confidence =
closer match (it's a distance), so we treat confidence below a threshold as a match.
"""
import json

import cv2
import numpy as np

from ruby.config import FACE_EMBEDDINGS_DIR, FACE_CONFIDENCE_THRESHOLD
from ruby.face.enroll import SAMPLES_DIR, SAMPLE_SIZE

MODEL_PATH = FACE_EMBEDDINGS_DIR / "trained_lbph.yml"
INDEX_PATH = SAMPLES_DIR / "index.json"


class FaceRecognizer:
    def __init__(self):
        self.model = cv2.face.LBPHFaceRecognizer_create()
        self.trained = False
        self.labels = {}          # id -> label name
        self.id_of = {}           # label name -> id

    def _load_index(self):
        """Rebuild label <-> id maps from the on-disk samples index."""
        self.labels, self.id_of = {}, {}
        if INDEX_PATH.exists():
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                mapping = json.load(f)  # {label: id}
            self.id_of = mapping
            self.labels = {v: k for k, v in mapping.items()}
        else:
            # Derive ids from directory order for backward compatibility.
            for label in sorted(SAMPLES_DIR.iterdir() if SAMPLES_DIR.is_dir() else []):
                if label.is_dir():
                    nid = len(self.id_of) + 1
                    self.id_of[label.name] = nid
                    self.labels[nid] = label.name

    def train_from_samples(self) -> int:
        """Train the LBPH model from all enrolled samples. Returns sample count."""
        self._load_index()
        samples, labels = [], []
        for label, nid in self.id_of.items():
            label_dir = SAMPLES_DIR / label
            if not label_dir.is_dir():
                continue
            for img in sorted(label_dir.glob("*.png")):
                gray = cv2.imread(str(img), cv2.IMREAD_GRAYSCALE)
                if gray is None:
                    continue
                samples.append(gray)
                labels.append(nid)
        if not samples:
            self.trained = False
            return 0
        self.model.train(np.asarray(samples, dtype=np.uint8),
                         np.asarray(labels, dtype=np.int32))
        self.trained = True
        self._save()
        return len(samples)

    def _save(self):
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.model.write(str(MODEL_PATH))
        SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(self.id_of, f, indent=2)

    def load(self) -> bool:
        if not MODEL_PATH.exists():
            return False
        self.model.read(str(MODEL_PATH))
        self._load_index()
        self.trained = True
        return True

    def recognize(self, gray_face, confidence_threshold: float = None):
        """Predict the owner for one face crop.

        Returns (label_or_None, confidence). None when nothing matches confidently
        (i.e. the face is not recognized as an enrolled owner).
        """
        if confidence_threshold is None:
            confidence_threshold = FACE_CONFIDENCE_THRESHOLD
        if not self.trained:
            self.load()
        if not self.trained:
            return None, float("inf")
        nid, confidence = self.model.predict(gray_face)
        label = self.labels.get(nid)
        if label is None or confidence > confidence_threshold:
            return None, float(confidence)
        return label, float(confidence)
