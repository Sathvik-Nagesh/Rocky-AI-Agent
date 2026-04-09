"""
Vector Database integration using ChromaDB.
This provides Long-Term Semantic Memory without bloating the prompt context window.
"""

import os
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# Use the default lightweight multi-qa-MiniLM-L6-cos-v1 embedding model automatically
_EMBED_FN = embedding_functions.DefaultEmbeddingFunction()

# Persistent storage folder inside the memory directory
_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

class VectorMemory:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=_DB_PATH, settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name="rocky_conversations",
            embedding_function=_EMBED_FN
        )

    def add_memory(self, user_text: str, rocky_resp: str):
        """Stores a conversational chunk as an embedding."""
        try:
            # We use the length of the collection as an auto-incrementing ID
            doc_id = f"mem_{self.collection.count() + 1}"
            
            # Combine the exchange into a single semantic document
            content = f"User said: {user_text}\nRocky replied: {rocky_resp}"
            
            self.collection.add(
                documents=[content],
                metadatas=[{"role": "conversation"}],
                ids=[doc_id]
            )
        except Exception as e:
            print(f"[VECTOR-DB] Failed to add memory: {e}")

    def search_memories(self, query: str, top_k: int = 3) -> list[str]:
        """Fetches the 3 most relevant previous memories for context."""
        try:
            if self.collection.count() == 0:
                return []
            
            # Query the database
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            if results and "documents" in results and results["documents"]:
                return results["documents"][0]
            return []
        except Exception as e:
            print(f"[VECTOR-DB] Failed to search memory: {e}")
            return []

# Singleton instance
vector_memory = VectorMemory()
