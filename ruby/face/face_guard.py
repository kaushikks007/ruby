"""FaceGuard — gates voice/actions on confirming the person on camera is the owner.

Used to wake Ruby and to confirm it's really the owner before acting on voice
commands. A single identity check consists of a face visibly in frame that the
recognizer matches reliably; we require several consecutive matching frames so a
single blurry frame doesn't spoof the gate. Fully local.
"""
import time

from ruby.face.camera import Camera
from ruby.face.detector import FaceDetector
from ruby.face.recognizer import FaceRecognizer
from ruby.face.enroll import SAMPLE_SIZE, count_samples, label_dir


class FaceGuard:
    def __init__(self, recognizer=None, detector=None, confidence_threshold: float = None):
        self.recognizer = recognizer or FaceRecognizer()
        self.detector = detector or FaceDetector()
        if confidence_threshold is None:
            from ruby.config import FACE_CONFIDENCE_THRESHOLD
            confidence_threshold = FACE_CONFIDENCE_THRESHOLD
        self.confidence_threshold = confidence_threshold

    def is_enrolled(self) -> bool:
        """True if at least one person has enrolled face samples on disk."""
        for label in sorted(label_dir("").parent.iterdir() if label_dir("").parent.is_dir() else []):
            if label.is_dir() and count_samples(label.name) >= 1:
                return True
        return self.recognizer.load()

    def confirm_user(
        self,
        required_frames: int = 5,
        timeout_seconds: float = 15.0,
        require_enrolled: bool = True,
        verbose: bool = True,
    ) -> dict:
        """Watch the webcam until the owner is confidently recognized.

        Returns {matched: bool, label: str|None, confidence: float, frames: int}.
        """
        if require_enrolled and not self.is_enrolled():
            if verbose:
                print("[face/guard] No enrolled face samples yet. Run face_enroll first.")
            return {"matched": False, "label": None, "confidence": float("inf"), "frames": 0}

        if not self.recognizer.load():
            if verbose:
                print("[face/guard] No trained model yet - training from samples.")
            n = self.recognizer.train_from_samples()
            if n == 0:
                return {"matched": False, "label": None, "confidence": float("inf"), "frames": 0}

        consecutive = 0
        best_label, best_conf = None, float("inf")
        start = time.time()

        with Camera() as cam:
            if not cam.read()[0]:
                if verbose:
                    print("[face/guard] Could not open webcam.")
                return {"matched": False, "label": None, "confidence": float("inf"), "frames": 0}
            while time.time() - start < timeout_seconds:
                ok, frame = cam.read()
                if not ok:
                    continue
                gray, rect = self.detector.largest_face(frame)
                if rect is None:
                    consecutive = 0
                    continue
                crop = self.detector.crop_face(gray, rect, SAMPLE_SIZE)
                if crop is None:
                    continue
                label, confidence = self.recognizer.recognize(crop, self.confidence_threshold)
                if label is not None:
                    consecutive += 1
                    if confidence < best_conf:
                        best_label, best_conf = label, confidence
                    if verbose:
                        print(f"[face/guard] match {consecutive}/{required_frames} "
                              f"({label}, conf={confidence:.1f})", flush=True)
                    if consecutive >= required_frames:
                        return {
                            "matched": True,
                            "label": best_label,
                            "confidence": best_conf,
                            "frames": consecutive,
                        }
                else:
                    consecutive = 0

        return {
            "matched": False,
            "label": best_label,
            "confidence": best_conf,
            "frames": consecutive,
        }
