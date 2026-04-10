import os
import logging

PLUGIN_DIR = "jarvis/plugins"

def create_plugin(name: str, code: str) -> str:
    """Create a new plugin file."""
    if not os.path.exists(PLUGIN_DIR):
        os.makedirs(PLUGIN_DIR)
        
    filename = f"{name.lower().replace(' ', '_')}.py"
    path = os.path.join(PLUGIN_DIR, filename)
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return f"Self-Evolution Complete: New plugin '{filename}' has been synthesized and integrated into my core."
    except Exception as e:
        return f"Evolution Failed: {e}"

def generate_plugin_logic(request: str) -> str:
    """Use the LLM to generate a new Python plugin based on a user request."""
    from brain.llm import generate_response
    
    prompt = (
        "You are an AI Architect. Generate a standalone Python plugin for Rocky.\n"
        "Requirements:\n"
        "1. Must define a function `run(action_data: str) -> str`.\n"
        "2. Must be clean, functional code.\n"
        "3. Focus ONLY on the code output.\n\n"
        f"User Request: {request}"
    )
    
    code = generate_response(prompt, [])
    # Strip markdown code blocks if any
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
        
    return code
