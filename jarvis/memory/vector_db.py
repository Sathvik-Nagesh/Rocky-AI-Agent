"""
Vector Database integration using ChromaDB.
Optimised: 
  - Cached count to avoid disk round-trips on every add
  - Skips search if DB is empty (avoids cold embedding calls)
  - Thread-safe ID generation via atomic counter
"""

import os
import threading
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

_EMBED_FN = embedding_functions.DefaultEmbeddingFunction()
_DB_PATH  = os.path.join(os.path.dirname(__file__), "chroma_db")


class VectorMemory:
    def __init__(self):
        self.client     = chromadb.PersistentClient(path=_DB_PATH, settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name="rocky_conversations",
            embedding_function=_EMBED_FN
        )
        # Cache count in-memory — avoids disk round-trip on every add()
        self._count     = self.collection.count()
        self._lock      = threading.Lock()

    # ── Write ──────────────────────────────────────────────────────────────────
    def add_memory(self, user_text: str, rocky_resp: str):
        """Store a conversational chunk. Thread-safe O(1) ID generation."""
        try:
            with self._lock:
                self._count += 1
                doc_id = f"mem_{self._count}"

            content = f"User said: {user_text}\nRocky replied: {rocky_resp}"
            self.collection.add(
                documents=[content],
                metadatas=[{"role": "conversation"}],
                ids=[doc_id]
            )
        except Exception as e:
            print(f"[VECTOR-DB] Add failed: {e}")

    # ── Read ───────────────────────────────────────────────────────────────────
    def search_memories(self, query: str, top_k: int = 2) -> list[str]:
        """
        Semantic search. Returns [] immediately if DB is empty —
        avoids spinning up the embedding model for brand-new sessions.
        """
        if self._count == 0:
            return []
        try:
            real_k = min(top_k, self._count)
            results = self.collection.query(query_texts=[query], n_results=real_k)
            if results and "documents" in results and results["documents"]:
                return results["documents"][0]
        except Exception as e:
            print(f"[VECTOR-DB] Search failed: {e}")
        return []

    def clear(self):
        """Drop the collection and recreate it empty."""
        try:
            with self._lock:
                self.client.delete_collection("rocky_conversations")
                self.collection = self.client.create_collection(
                    name="rocky_conversations",
                    embedding_function=_EMBED_FN
                )
                self._count = 0
        except Exception as e:
            print(f"[VECTOR-DB] Clear failed: {e}")

    def get_all(self) -> list[str]:
        """Retrieve all documents (used by exporter)."""
        try:
            return self.collection.get().get("documents", [])
        except Exception:
            return []


# Singleton — loaded once at import time
vector_memory = VectorMemory()
