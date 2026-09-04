"""
Live self-test for Phase 5 face recognition.

Run:
    .\.venv\Scripts\python.exe scripts\face_verify_live.py [seconds]

Opens the webcam and prints a verdict each frame: whether the person is
recognized as the enrolled owner, with LBPH confidence (lower = better).
Close the preview window (or Ctrl+C) to stop.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from ruby.face.camera import Camera
from ruby.face.detector import FaceDetector
from ruby.face.recognizer import FaceRecognizer
from ruby.face.enroll import SAMPLE_SIZE
from ruby.config import FACE_CONFIDENCE_THRESHOLD


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
    detector = FaceDetector()
    recognizer = FaceRecognizer()

    if not recognizer.load():
        print("No trained model - training from samples ...")
        n = recognizer.train_from_samples()
        if n == 0:
            print("No enrolled samples found. Run scripts/face_enroll.py first.")
            return
        print(f"Trained on {n} samples.")

    print("Look at the camera. 'q' or close window to quit.")
    start = time.time()
    with Camera() as cam:
        if not cam.read()[0]:
            print("Could not open webcam.")
            return
        while time.time() - start < duration:
            ok, frame = cam.read()
            if not ok:
                continue
            gray, rect = detector.largest_face(frame)
            h, w = frame.shape[:2]
            if rect:
                x, y, rw, rh = rect
                cv2.rectangle(frame, (x, y), (x + rw, y + rh), (0, 255, 0), 2)
                crop = detector.crop_face(gray, rect, SAMPLE_SIZE)
                label, conf = recognizer.recognize(crop, FACE_CONFIDENCE_THRESHOLD)
                verdict = f"MATCH {label}" if label else "NOT OWNER"
                color = (0, 255, 0) if label else (0, 0, 255)
                cv2.putText(frame, f"{verdict} conf={conf:.0f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            else:
                cv2.putText(frame, "NO FACE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 165, 255), 2)
            cv2.imshow("Ruby Face Verify", frame)
            if (cv2.waitKey(1) & 0xFF) == ord("q"):
                break
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
