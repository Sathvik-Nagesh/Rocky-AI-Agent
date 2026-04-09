"""
Conversation Exporter.
Dumps ChromaDB history and short-term memory to a clean Markdown file.
"""

import os
import datetime
from memory.vector_db import vector_memory
from memory.memory_manager import load_memory

def export_history(filename: str = None) -> str:
    """Exports all memories to a markdown file on the Desktop."""
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Rocky_Log_{timestamp}.md"
    
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    filepath = os.path.join(desktop, filename)
    
    try:
        # 1. Gather short-term history
        memory = load_memory()
        history = memory.get("history", [])
        
        # 2. Gather long-term vector history (all items)
        # We query for everything by using an empty string and a large limit
        vector_res = vector_memory.collection.get()
        documents = vector_res.get("documents", [])
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Rocky Assistant Conversation Log\n")
            f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"## Recent Exchanges (Short-Term Memory)\n")
            for entry in history:
                f.write(f"**USER**: {entry.get('user')}\n")
                f.write(f"**ROCKY**: {entry.get('assistant')}\n\n")
            
            f.write(f"---\n")
            f.write(f"## Archived Memories (Vector DB)\n")
            for doc in documents:
                f.write(f"> {doc}\n\n")
                
        return f"Exported {len(history) + len(documents)} memories to {filename} on your Desktop."
    except Exception as e:
        return f"Export failed: {e}"
