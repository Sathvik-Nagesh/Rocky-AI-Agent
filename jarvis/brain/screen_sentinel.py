import threading
import time
import logging
import pyautogui
from PIL import Image
try:
    import pytesseract
except ImportError:
    pytesseract = None

class ScreenSentinel:
    def __init__(self, on_insight=None, interval=60):
        self.on_insight = on_insight
        self.interval = interval
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if not pytesseract:
            logging.warning("pytesseract not found. Screen Sentinel disabled.")
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)

    def _run(self):
        while not self.stop_event.is_set():
            try:
                # 1. Take screenshot
                screenshot = pyautogui.screenshot()
                
                # 2. OCR everything (this is slow, so we do it in a thread)
                text = pytesseract.image_to_string(screenshot)
                
                # 3. Analyze for critical patterns
                insights = self._analyze_text(text)
                if insights and self.on_insight:
                    for insight in insights:
                        self.on_insight(insight)
                        
            except Exception as e:
                logging.error(f"Screen Sentinel Error: {e}")
            
            # Wait for next cycle
            time.sleep(self.interval)

    def _analyze_text(self, text: str) -> list[str]:
        results = []
        low = text.lower()
        
        # Look for typical error patterns
        if "traceback (most recent call last)" in low or "exception" in low:
            results.append("I noticed a Python Traceback on your screen. Need help debugging?")
        
        if "error:" in low or "failed to" in low:
            results.append("A process seems to have failed. I'm standing by if you need an audit.")
            
        if "import error" in low or "modulenotfounderror" in low:
            results.append("Spotted a missing module error. Want me to generate a fix script?")

        return results
