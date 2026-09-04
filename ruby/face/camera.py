"""Minimal webcam wrapper around OpenCV, with Windows DirectShow first (faster
startup, avoids the MSMF auto-exposure lag common on laptops)."""
import cv2


class Camera:
    def __init__(self, index: int = 0):
        self.index = index
        self.cap = None

    def open(self) -> bool:
        # DirectShow is the reliable backend on Windows; fall back to default.
        self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.index)
        return self.cap.isOpened()

    def read(self):
        if self.cap is None or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.release()
        return False
