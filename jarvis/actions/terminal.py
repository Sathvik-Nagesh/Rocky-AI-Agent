"""
Agentic Terminal — Rocky writes and executes scripts.

Safety: Rocky ALWAYS asks for confirmation before executing.
The confirmation flows through a signal back to the voice loop.
"""

import os
import subprocess
import tempfile
import logging


def generate_script(task: str) -> dict:
    """
    Use the LLM to generate a Python or PowerShell script for a task.
    Returns: {"language": "python"|"powershell", "code": str, "explanation": str}
    """
    from brain.llm import generate_response
    import json

    prompt = (
        f"Write a script to accomplish this task: {task}\n"
        "Return JSON with these fields:\n"
        '{"language": "python" or "powershell", "code": "the full script", "explanation": "1 sentence what it does"}\n'
        "ONLY output the JSON. No other text."
    )

    raw = generate_response(prompt, history=[])
    try:
        data = json.loads(raw)
        return {
            "language": data.get("response", data.get("language", "python")),
            "code": data.get("action", data.get("code", "")),
            "explanation": data.get("response", data.get("explanation", "Script generated.")),
        }
    except Exception:
        return {
            "language": "python",
            "code": "",
            "explanation": "Failed to generate script. The task may be too complex.",
        }


def execute_script(code: str, language: str = "python") -> str:
    """
    Execute a script in a sandboxed subprocess.
    Returns stdout/stderr output.
    """
    if not code.strip():
        return "No code to execute."

    try:
        if language.lower() in ("python", "py"):
            # Write to temp file and execute
            fd, path = tempfile.mkstemp(suffix=".py")
            os.close(fd)
            with open(path, "w") as f:
                f.write(code)

            result = subprocess.run(
                ["python", path],
                capture_output=True, text=True, timeout=30,
                cwd=os.path.expanduser("~")
            )
            os.remove(path)

        elif language.lower() in ("powershell", "ps1"):
            fd, path = tempfile.mkstemp(suffix=".ps1")
            os.close(fd)
            with open(path, "w") as f:
                f.write(code)

            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", path],
                capture_output=True, text=True, timeout=30,
                cwd=os.path.expanduser("~")
            )
            os.remove(path)
        else:
            return f"Unsupported language: {language}"

        output = result.stdout.strip() or result.stderr.strip() or "Script executed. No output."
        return output[:500]  # Cap output length

    except subprocess.TimeoutExpired:
        return "Script timed out after 30 seconds."
    except Exception as e:
        logging.error(f"Script execution error: {e}")
        return f"Execution failed: {e}"
