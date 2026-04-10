import os
import subprocess
import logging
import json

def initiate_genesis(project_name: str, description: str) -> str:
    """Scaffold a full project from scratch."""
    print(f"[GENESIS] Summoning Project: {project_name}...")
    
    root_dir = os.path.join(os.getcwd(), "scaffolded_projects", project_name.lower().replace(" ", "_"))
    if os.path.exists(root_dir):
        return f"Project Genesis stalled: A project named '{project_name}' already exists in your workspace."

    from brain.llm import generate_response
    
    # Step 1: Architect planning
    plan_prompt = (
        "You are the Architect within Project Genesis.\n"
        f"Create a full file-system structure for a project: {project_name}\n"
        f"Description: {description}\n"
        "Return ONLY a JSON list of file paths (e.g. ['src/main.py', 'README.md'])."
    )
    
    plan_reply = generate_response(plan_prompt, [])
    try:
        # Extract JSON list
        if "```json" in plan_reply:
            plan_reply = plan_reply.split("```json")[1].split("```")[0].strip()
        files_to_create = json.loads(plan_reply)
    except Exception as e:
        return f"Genesis failed during architect planning: {e}"

    # Step 2: Physical Creation
    os.makedirs(root_dir, exist_ok=True)
    created_files = []
    
    for relative_path in files_to_create:
        full_path = os.path.join(root_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Step 3: Write boilerplate
        code_prompt = (
            f"Write the initial boilerplate code for the file: {relative_path}\n"
            f"This is part of the project: {project_name} ({description})\n"
            "Focus on clean, functional code. No conversational text."
        )
        code = generate_response(code_prompt, [])
        if "```" in code: # Strip markdown
            code = code.split("```")[1].split("```")[0].strip()
        if code.startswith("python") or code.startswith("go") or code.startswith("javascript"):
            code = "\n".join(code.split("\n")[1:])

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)
        created_files.append(relative_path)

    # Step 4: Git Init
    try:
        subprocess.run(["git", "init"], cwd=root_dir, capture_output=True)
    except:
        pass

    return f"Project Genesis Complete: '{project_name}' has been summoned with {len(created_files)} files in {root_dir}."
