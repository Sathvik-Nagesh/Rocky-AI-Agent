"""
Plugin Manager — allows dynamically loading smart home / API extensions.
Users drop scripts in the `plugins/` directory and they are automatically loaded.
"""

import os
import importlib
import inspect

PLUGINS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins")
_plugins = {}

def load_plugins():
    """Scan the plugins directory and load valid python modules."""
    global _plugins
    if not os.path.exists(PLUGINS_DIR):
        os.makedirs(PLUGINS_DIR)
        
    for filename in os.listdir(PLUGINS_DIR):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = filename[:-3]
            try:
                # Load module dynamically
                spec = importlib.util.spec_from_file_location(module_name, os.path.join(PLUGINS_DIR, filename))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Check for an entrypoint function 'execute'
                if hasattr(module, 'execute') and hasattr(module, 'KEYWORDS'):
                    _plugins[module_name] = module
                    print(f"[PLUGINS] Loaded extension: {module_name}")
            except Exception as e:
                print(f"[PLUGINS] Failed to load {module_name}: {e}")

def run_plugin(query: str) -> str | None:
    """Check if the query matches any plugin keywords and execute it."""
    low = query.lower()
    for name, module in _plugins.items():
        if any(kw in low for kw in module.KEYWORDS):
            try:
                result = module.execute(query)
                return result
            except Exception as e:
                print(f"[PLUGINS] Error executing {name}: {e}")
                return "Plugin failure. The module encountered an error."
    return None

# Auto-load on boot
load_plugins()
