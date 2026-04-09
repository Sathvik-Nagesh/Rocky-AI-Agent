"""
Vision Phase 2: Presence Sensing (The Loyalty Module).
Uses cv2 to monitor if a user is currently at their desk.
Triggers an auto-welcome or auto-lock depending on presence state.
"""

import threading
import time
import logging

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False
    logging.warning("opencv-python not installed. Presence Sensing disabled.")

_POLL_INTERVAL = 3.0    # check every 3s
_AFK_TIMEOUT   = 120.0  # seconds without a face to be considered AFK


class PresenceSensor:
    def __init__(self, on_presence_change=None):
        self._callback = on_presence_change
        self._stop     = threading.Event()
        self._thread   = None
        self._present  = True
        self._last_seen = time.time()
        self._face_cascade = None
        
        if _CV2_AVAILABLE:
            try:
                # Load pre-trained haarcascade for face detection (fast, low CPU)
                self._face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            except Exception as e:
                logging.error(f"Failed to load face cascade: {e}")

    def start(self):
        if not _CV2_AVAILABLE or not self._face_cascade:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logging.info("PresenceSensor started.")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _poll_loop(self):
        cap = cv2.VideoCapture(0)
        # Lower resolution to save CPU
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        while not self._stop.is_set():
            ret, frame = cap.read()
            if not ret:
                time.sleep(_POLL_INTERVAL)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self._face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(30, 30))
            
            face_detected = len(faces) > 0
            now = time.time()

            if face_detected:
                if not self._present and (now - self._last_seen) > _AFK_TIMEOUT:
                    # User returned after being AFK
                    self._present = True
                    if self._callback:
                        self._callback("returned")
                self._last_seen = now
            else:
                if self._present and (now - self._last_seen) > _AFK_TIMEOUT:
                    # User went AFK
                    self._present = False
                    if self._callback:
                        self._callback("afk")

            time.sleep(_POLL_INTERVAL)
            
        cap.release()
