"""
Shadow Learner: Implicit RAG
Automatically monitors the filesystem and indexes new files into vector memory
so Rocky "implicitly" knows what the user is working on.
"""
import os
import time
import logging
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from brain.file_rag import _read_text_file, _read_pdf, _chunk_text, _get_doc_collection, _TEXT_EXTENSIONS

class ShadowHandler(FileSystemEventHandler):
    def __init__(self, signals=None):
        self.signals = signals
        self._last_processed = {} # path -> time

    def on_modified(self, event):
        if not event.is_directory:
            self._process(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._process(event.src_path)

    def _process(self, filepath):
        # Prevent double-processing (some OS events fire twice)
        now = time.time()
        if filepath in self._last_processed and now - self._last_processed[filepath] < 2:
            return
        self._last_processed[filepath] = now

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in _TEXT_EXTENSIONS and ext != ".pdf":
            return

        # Background thread to avoid blocking the OS watcher
        threading.Thread(target=self._ingest, args=(filepath, ext), daemon=True).start()

    def _ingest(self, filepath, ext):
        try:
            # Wait a split second for file write to finish
            time.sleep(0.5)
            
            text = ""
            if ext == ".pdf":
                text = _read_pdf(filepath)
            else:
                text = _read_text_file(filepath)

            if not text or len(text) < 50:
                return

            collection = _get_doc_collection()
            chunks = _chunk_text(text, filepath)
            
            for chunk in chunks:
                doc_id = f"shadow_{chunk['hash']}"
                collection.upsert(
                    documents=[chunk["text"]],
                    metadatas=[{"source": filepath, "role": "shadow_learner", "timestamp": time.time()}],
                    ids=[doc_id]
                )
            
            if self.signals:
                self.signals.info_text.emit(f"🧠 Implicitly learned: {os.path.basename(filepath)}")
                print(f"[SHADOW LEARNER] Indexed: {filepath}")

        except Exception as e:
            logging.debug(f"Shadow Learner error on {filepath}: {e}")

class ShadowLearner:
    def __init__(self, signals=None):
        self.signals = signals
        self.observer = Observer()
        self.paths = [
            os.path.join(os.path.expanduser("~"), "Documents"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "Downloads")
        ]

    def start(self):
        handler = ShadowHandler(self.signals)
        for path in self.paths:
            if os.path.exists(path):
                self.observer.schedule(handler, path, recursive=False) # Shallow watch for speed
                print(f"[SHADOW LEARNER] Watching: {path}")
        
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
