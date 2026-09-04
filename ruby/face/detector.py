"""Face detection via a bundled Haar cascade (fully local, no cloud)."""
from pathlib import Path

import cv2

_CASCADE_PATH = Path(__file__).parent / "data" / "haarcascade_frontalface_default.xml"


class FaceDetector:
    def __init__(self, cascade_path=None):
        self.cascade = cv2.CascadeClassifier(str(cascade_path or _CASCADE_PATH))
        if self.cascade.empty():
            raise RuntimeError(f"Face cascade failed to load from {_CASCADE_PATH}")

    def detect(self, frame_bgr, min_size=(60, 60)):
        """Return (gray_frame, list_of_(x, y, w, h) rects)."""
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self.cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=min_size
        )
        return gray, list(faces)

    def largest_face(self, frame_bgr, min_size=(60, 60)):
        """Return (gray_frame, (x, y, w, h)|None) for the biggest face present."""
        gray, faces = self.detect(frame_bgr, min_size=min_size)
        if not faces:
            return gray, None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        return gray, (x, y, w, h)

    def crop_face(self, gray, rect, size=(100, 100)):
        """Extract a normalized grayscale crop of a face rect for storage/predict."""
        x, y, w, h = rect
        x = max(0, x)
        y = max(0, y)
        face = gray[y : y + h, x : x + w]
        if face.size == 0:
            return None
        return cv2.resize(face, size)
