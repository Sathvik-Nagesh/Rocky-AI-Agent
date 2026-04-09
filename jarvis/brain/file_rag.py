"""
Local Document RAG — "File Sense"

Ingests files from user-specified folders into ChromaDB so Rocky can
answer questions about the user's own documents, code, and notes.

Supports: .txt, .md, .py, .js, .ts, .json, .csv, .log, .html, .css
PDF support requires `pymupdf` (fitz) — optional.
"""

import os
import logging
import hashlib
from pathlib import Path

from memory.vector_db import vector_memory

# File types we can read natively
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".csv", ".log", ".html", ".css", ".yaml", ".yml",
    ".toml", ".cfg", ".ini", ".sh", ".bat", ".ps1",
    ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb",
}

# Max characters per chunk (ChromaDB works best with ~500-1000 token chunks)
_CHUNK_SIZE = 1500
_CHUNK_OVERLAP = 200


def _read_text_file(path: str) -> str:
    """Read a plain text file with encoding fallback."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, PermissionError):
            continue
    return ""


def _read_pdf(path: str) -> str:
    """Read PDF text using pymupdf if available."""
    try:
        import fitz  # pymupdf
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except ImportError:
        logging.debug("pymupdf not installed — skipping PDF.")
        return ""
    except Exception as e:
        logging.error(f"PDF read error for {path}: {e}")
        return ""


def _chunk_text(text: str, source: str) -> list[dict]:
    """Split text into overlapping chunks for embedding."""
    chunks = []
    for i in range(0, len(text), _CHUNK_SIZE - _CHUNK_OVERLAP):
        chunk = text[i : i + _CHUNK_SIZE].strip()
        if len(chunk) < 50:  # Skip tiny fragments
            continue
        chunks.append({
            "text":   chunk,
            "source": source,
            "hash":   hashlib.md5(chunk.encode()).hexdigest()[:12],
        })
    return chunks


def _get_doc_collection():
    """Get or create a separate ChromaDB collection for documents."""
    return vector_memory.client.get_or_create_collection(
        name="rocky_documents",
        embedding_function=vector_memory.collection._embedding_function
    )


def ingest_folder(folder_path: str) -> dict:
    """
    Recursively scan a folder, read supported files, chunk them,
    and store the embeddings in ChromaDB.

    Returns stats dict: {"files_processed": int, "chunks_added": int, "errors": int}
    """
    folder = Path(folder_path).expanduser().resolve()
    if not folder.exists():
        return {"error": f"Folder does not exist: {folder}"}

    collection = _get_doc_collection()
    stats = {"files_processed": 0, "chunks_added": 0, "errors": 0}

    print(f"[FILE-RAG] Scanning: {folder}")

    for root, dirs, files in os.walk(folder):
        # Skip hidden dirs and common junk
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   {"node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build"}]

        for filename in files:
            filepath = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1].lower()

            text = ""
            if ext in _TEXT_EXTENSIONS:
                text = _read_text_file(filepath)
            elif ext == ".pdf":
                text = _read_pdf(filepath)
            else:
                continue

            if not text or len(text) < 50:
                continue

            try:
                chunks = _chunk_text(text, filepath)
                for chunk in chunks:
                    doc_id = f"doc_{chunk['hash']}"
                    collection.upsert(
                        documents=[chunk["text"]],
                        metadatas=[{"source": chunk["source"], "role": "document"}],
                        ids=[doc_id]
                    )
                stats["files_processed"] += 1
                stats["chunks_added"] += len(chunks)
            except Exception as e:
                logging.error(f"Ingest error for {filepath}: {e}")
                stats["errors"] += 1

    print(f"[FILE-RAG] Done. Files: {stats['files_processed']}, Chunks: {stats['chunks_added']}")
    return stats


def query_documents(question: str, top_k: int = 3) -> list[str]:
    """Search ingested documents for relevant content."""
    try:
        collection = _get_doc_collection()
        if collection.count() == 0:
            return []

        results = collection.query(query_texts=[question], n_results=top_k)
        if results and "documents" in results and results["documents"]:
            return results["documents"][0]
        return []
    except Exception as e:
        logging.error(f"Document query error: {e}")
        return []
