"""
Self-Correction Reflection Loop
Analyzes past interaction failures and generates dynamic rules to improve performance.
"""
import os
import json
import logging
from brain.llm import generate_response

RULES_FILE = os.path.join("memory", "dynamic_rules.txt")
HISTORY_FILE = os.path.join("memory", "history.json") # Assuming history is saved here

def run_reflection():
    """Analyze recent history and update dynamic rules."""
    if not os.path.exists(HISTORY_FILE):
        return "No history found for reflection."

    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        
        # Take the last 20 exchanges
        recent = history[-20:] if len(history) > 20 else history
        
        reflection_prompt = f"""
        Analyze the following conversation history between a human and an AI assistant named Rocky.
        Identify any mistakes, misinterpretations, or failures to execute capabilities.
        
        Generate a set of 3-5 concise "Instruction Rules" that the assistant should follow to avoid these mistakes in the future.
        Format:
        1. [Rule]
        2. [Rule]
        
        History:
        {json.dumps(recent, indent=2)}
        """
        
        raw_rules = generate_response(reflection_prompt, [])
        # Simple extraction
        if "1." in raw_rules:
            rules_text = raw_rules[raw_rules.find("1."):].strip()
            with open(RULES_FILE, "w") as f:
                f.write(rules_text)
            return f"Reflection complete. {len(rules_text.splitlines())} new rules established."
        
        return "Reflection completed, but no specific new rules were needed."

    except Exception as e:
        logging.error(f"Reflection error: {e}")
        return f"Reflection failed: {e}"

def get_dynamic_rules() -> str:
    """Read the rules for injection into the prompt."""
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, "r") as f:
            return f.read()
    return ""
