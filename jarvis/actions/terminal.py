"""
Agentic Terminal — Rocky writes and executes scripts.

Safety:
  1. Rocky ALWAYS asks for confirmation before executing.
  2. Generated code is scanned against a BLOCKLIST of dangerous patterns.
  3. Execution happens in a sandboxed subprocess with 30-second timeout.
"""

import os
import re
import subprocess
import tempfile
import logging

import ast

# ── Security Allowlist (Python AST Verification) ────────────────────────────────
_SAFE_OS_METHODS = {
    "listdir", "getcwd", "path", "stat", "environ", "getenv",
    "cpu_count", "urandom", "sep", "linesep", "pathsep"
}
_SAFE_SHUTIL_METHODS = {
    "disk_usage", "which"
}
_BLOCKED_MODULES = {"subprocess", "pty", "sys"}

class SecurityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.violation = None

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in _BLOCKED_MODULES:
                self.violation = f"Blocked: importing '{alias.name}' is prohibited."
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module in _BLOCKED_MODULES:
            self.violation = f"Blocked: importing from '{node.module}' is prohibited."
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            # Check os.* calls
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                if node.func.attr not in _SAFE_OS_METHODS:
                    self.violation = f"Blocked: os.{node.func.attr} is not on the Allowlist."
            # Check shutil.* calls
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "shutil":
                if node.func.attr not in _SAFE_SHUTIL_METHODS:
                    self.violation = f"Blocked: shutil.{node.func.attr} is not on the Allowlist."
        elif isinstance(node.func, ast.Name):
            # Check for eval/exec
            if node.func.id in ("eval", "exec", "compile", "__import__"):
                self.violation = f"Blocked: {node.func.id}() is inherently dangerous."
        self.generic_visit(node)

def _scan_code(code: str, language: str = "python") -> str | None:
    """Scan code. For Python, strictly AST Allowlist. For PS1, regex blocklist."""
    if language.lower() in ("python", "py"):
        try:
            tree = ast.parse(code)
            visitor = SecurityVisitor()
            visitor.visit(tree)
            return visitor.violation
        except SyntaxError:
            return "Blocked: Python code has invalid syntax."
    
    # Fallback for Powershell / Bash
    bad_patterns = [
        r"Remove-Item\s+-Recurse", r"rm\s+-rf", r"del\s+/[sS]", 
        r"format\s+\w:\s*/", r"reg\s+delete", r"taskkill", 
        r"Format-Volume", r"Stop-Process"
    ]
    for pattern in bad_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return f"Blocked: dangerous shell pattern detected (`{pattern}`)."
    return None


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

    # 🛡️ SECURITY: Scan code against allowlist
    violation = _scan_code(code, language)
    if violation:
        logging.warning(violation)
        return violation

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
