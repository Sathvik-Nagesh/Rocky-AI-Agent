"""
Intelligent File Organizer (The "Chaos Fixer").
Organizes messy folders (like Desktop, Downloads) by extension and LLM context.
"""

import os
import shutil
import logging

# Basic extension mapping for fast sorting
_EXT_MAP = {
    ".pdf": "Documents", ".docx": "Documents", ".doc": "Documents", ".txt": "Documents",
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images", ".svg": "Images",
    ".mp4": "Videos", ".mov": "Videos", ".mkv": "Videos",
    ".mp3": "Audio", ".wav": "Audio",
    ".zip": "Archives", ".rar": "Archives", ".7z": "Archives", ".tar": "Archives", ".gz": "Archives",
    ".exe": "Executables", ".msi": "Executables",
    ".py": "Code", ".js": "Code", ".html": "Code", ".css": "Code", ".json": "Code"
}

def organize_folder(folder_path: str) -> str:
    """Sort files in a folder into categorical subdirectories."""
    if not os.path.exists(folder_path):
        return f"Folder {folder_path} doesn't exist."

    files_moved = 0
    errors = 0

    try:
        entries = os.listdir(folder_path)
    except PermissionError:
        return f"Access denied to read {folder_path}."

    for entry in entries:
        full_path = os.path.join(folder_path, entry)
        
        # Skip directories
        if os.path.isdir(full_path):
            continue
            
        # Get extension
        _, ext = os.path.splitext(entry)
        ext = ext.lower()
        
        if not ext:
            continue
            
        category = _EXT_MAP.get(ext, "Other")
        
        target_dir = os.path.join(folder_path, category)
        try:
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                
            shutil.move(full_path, os.path.join(target_dir, entry))
            files_moved += 1
        except Exception as e:
            logging.debug(f"Failed to move {entry}: {e}")
            errors += 1

    if files_moved == 0:
        return f"Folder is already organized. No loose files found."
        
    return f"Organized {files_moved} files into neat categories. {errors} errors."
