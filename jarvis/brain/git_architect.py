"""
Git & Code Architect for Rocky.
Allows Rocky to analyze git repositories, summarize diffs, and audit code logic.
"""

import os
import subprocess
import logging
from brain.llm import generate_response

def _run_git(args: list[str]) -> str:
    """Run a git command in the current directory."""
    cwd = os.getcwd()
    try:
        proc = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=10)
        return proc.stdout.strip() if proc.returncode == 0 else ""
    except Exception as e:
        logging.error(f"Git command failed: {e}")
        return ""

def summarize_repo_changes() -> str:
    """Get git status and uncommitted diff, then summarize with LLM."""
    if not os.path.exists(".git"):
        return "This is not a Git repository. Cannot analyze."

    status = _run_git(["status", "-s"])
    if not status:
        return "Repository is clean. No uncommitted changes."

    diff = _run_git(["diff"])
    # If no unstaged diff, check staged
    if not diff:
        diff = _run_git(["diff", "--cached"])

    if not diff:
        return f"Changes detected but no diff available:\n{status}"

    # Truncate diff if it's too large for LLM
    truncated_diff = diff[:4000]

    prompt = (
        "You are an expert Principal Engineer.\n"
        "Summarize these uncommitted git changes in 2 brief, Punchy sentences.\n"
        "Focus on what feature or bug was changed, not line-by-line.\n\n"
        f"Diff:\n{truncated_diff}"
    )

    summary = generate_response(prompt, history=[])
    
    # Strip json wrapper if exists
    if summary.startswith("{"):
        import json
        try:
            summary = json.loads(summary).get("response", summary)
        except:
            pass

    return f"Git Analysis: {summary.strip()}"


def audit_file(filename: str) -> str:
    """Runs a quick static code audit on a file."""
    if not os.path.exists(filename):
        return f"File '{filename}' does not exist."
        
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"Failed to read file: {e}"
        
    prompt = (
        f"You are a Senior Security & Code Auditor.\n"
        f"Audit this file: {filename}\n"
        "Point out ONE critical logical flaw or security risk.\n"
        "Keep it to exactly 2 sentences. Be harsh and direct.\n\n"
        f"Code:\n{content[:4000]}"
    )
    
    audit = generate_response(prompt, history=[])
    if audit.startswith("{"):
        import json
        try:
            audit = json.loads(audit).get("response", audit)
        except:
            pass

    return f"Audit for {os.path.basename(filename)}: {audit.strip()}"
    

def commit_changes(message: str) -> str:
    """Stage all changes and commit with a message."""
    if not os.path.exists(".git"):
        return "Not a git repository."
    
    # 1. Stage all
    _run_git(["add", "."])
    
    # 2. Get a better message from LLM if default is generic
    if not message or len(message) < 5:
        diff = _run_git(["diff", "--cached"])[:2000]
        prompt = f"Generate a concise, 1-sentence git commit message for these changes:\n{diff}"
        message = generate_response(prompt, [])
        if message.startswith("{"):
            import json
            try: message = json.loads(message).get("response", message)
            except: pass
            
    # 3. Commit
    result = _run_git(["commit", "-m", message])
    if "nothing to commit" in result.lower():
        return "Nothing to commit, working tree clean."
    
    return f"Changes committed: {message}"


def push_changes(branch: str = "main") -> str:
    """Push committed changes to origin."""
    # We use a longer timeout for push as it's a network operation
    print(f"[GIT] Pushing to origin {branch}...")
    try:
        # Check current branch if none provided
        if not branch or branch == "main":
            current = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
            branch = current or "main"
            
        proc = subprocess.run(["git", "push", "origin", branch], capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            return f"Successfully pushed to origin {branch}."
        else:
            return f"Push failed: {proc.stderr.strip()}"
    except Exception as e:
        return f"Push operation timed out or failed: {e}"
