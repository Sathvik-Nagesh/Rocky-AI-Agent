import subprocess
import sys
import os
import time
import logging

def auto_heal(error_msg: str):
    """Use the LLM to generate a fix for the captured traceback."""
    print(f"[SOVEREIGN] Critical failure detected. Analyzing trauma...")
    
    from brain.llm import generate_response
    prompt = (
        "You are the Sovereign Self-Healing Core for Rocky.\n"
        "The following crash occured in your system:\n"
        f"{error_msg}\n\n"
        "1. Identify the file and line causing the error.\n"
        "2. Provide the corrected block of code.\n"
        "3. Format your response as: FILE: <path>\nOLD: <old_code>\nNEW: <new_code>"
    )
    
    correction = generate_response(prompt, [])
    print(f"[SOVEREIGN] Patch synthesized. Applying fix...")
    
    try:
        # Simple parser for the healing response
        lines = correction.split('\n')
        file_path = ""
        old_code = []
        new_code = []
        target = None
        
        for line in lines:
            if line.startswith("FILE:"): file_path = line.replace("FILE:", "").strip()
            elif line.startswith("OLD:"): target = "old"
            elif line.startswith("NEW:"): target = "new"
            else:
                if target == "old": old_code.append(line)
                elif target == "new": new_code.append(line)
        
        if file_path and old_code and new_code:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            old_str = "\n".join(old_code).strip()
            new_str = "\n".join(new_code).strip()
            
            if old_str in content:
                new_content = content.replace(old_str, new_str)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"[SOVEREIGN] Successfully patched {file_path}. Rebooting...")
                return True
    except Exception as e:
        print(f"[SOVEREIGN] Healing procedure failed: {e}")
    return False

def run_with_watchdog():
    """Run jarvis/main.py and watch for crashes."""
    while True:
        print("[SOVEREIGN] Sentinel active. Launching Rocky core...")
        # Use sys.executable to ensure we use the same venv
        proc = subprocess.Popen([sys.executable, "jarvis/main.py"], stderr=subprocess.PIPE, text=True)
        
        # Capture stderr in a way that doesn't block
        _, stderr = proc.communicate()
        
        if proc.returncode != 0 and stderr:
            print(f"[SOVEREIGN] Core collapsed with error:\n{stderr}")
            if auto_heal(stderr):
                time.sleep(2) # Brief cooldown for file write
                continue # Restart
            else:
                print("[SOVEREIGN] Healing failed or no fix found. Manual intervention required.")
                break
        else:
            print("[SOVEREIGN] Core closed gracefully.")
            break

if __name__ == "__main__":
    run_with_watchdog()
