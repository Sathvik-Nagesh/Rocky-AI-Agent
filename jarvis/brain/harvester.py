import os
import logging
from memory.vector_db import vector_memory

# Files we want to "eat"
TARGET_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.html', '.css', '.md', '.txt', '.go', '.rs', '.json'}

def harvest_directory(root_path: str):
    """Recursively index all files in a directory."""
    print(f"[HARVESTER] Consuming context from: {root_path}")
    count = 0
    
    for root, dirs, files in os.walk(root_path):
        # Skip hidden and vendor dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', 'venv', '__pycache__', 'dist', 'build'}]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in TARGET_EXTENSIONS:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if len(content.strip()) < 50: continue # Skip trivial files
                        
                        # Add to vector memory with source metadata
                        metadata = f"Source: {file_path}\n"
                        vector_memory.add_memory(f"Content of {file}:", f"{metadata}{content[:10000]}") # Cap at 10k chars per file
                        count += 1
                except Exception as e:
                    logging.error(f"Harvester failed to read {file_path}: {e}")

    return f"Harvester Complete: {count} files assimilated into my local knowledge base."

if __name__ == "__main__":
    # Test on project root
    print(harvest_directory("."))
