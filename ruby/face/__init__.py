"""
Ruby Face — Phase 5: local-only face recognition.

Detects and recognizes the owner (kaushik) via the webcam using OpenCV. Everything
runs on-device: face crops + an LBPH recognizer model are stored under
memory/face_embeddings/ and never leave this PC. Used to wake Ruby and confirm
it's really the owner before acting on voice commands.
"""
from ruby.face.detector import FaceDetector
from ruby.face.recognizer import FaceRecognizer
from ruby.face.face_guard import FaceGuard
from ruby.face.enroll import save_sample, count_samples

__all__ = [
    "FaceDetector",
    "FaceRecognizer",
    "FaceGuard",
    "save_sample",
    "count_samples",
]
