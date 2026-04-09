"""
Action executor — routes parsed intent to the correct action function.
"""
import logging
from actions.system import (
    open_app, play_music, system_control, search_web, navigate_to,
    open_downloads, open_documents, open_desktop, find_file, WEBSITE_MAP,
)
from actions.weather import get_weather
from actions.web_agent import run_web_task
from brain.vision import analyze_screen

def execute_action(data: dict) -> str | None:
    """
    Execute action from intent dict.
    Returns an optional string to inject into Rocky's spoken response.
    """
    if not isinstance(data, dict):
        return None

    intent = (data.get("intent") or "chat").lower().strip()
    action = (data.get("action") or "").lower().strip()

    try:
        if intent == "plugin_action":
            # The plugin text response has already been generated
            return data.get("response_override", "Plugin executed.")

        elif intent == "deep_research":
            from actions.web_agent import run_mercenary_swarm
            raw_data = run_mercenary_swarm(action)
            if "Data extracted from" in raw_data or "Intelligence gathered" in raw_data:
                # Ask LLM to summarize
                from brain.llm import generate_response
                summary_prompt = f"Summarize this multi-agent research gathered for the user: {raw_data}"
                summary = generate_response(summary_prompt, [])
                # Extract response field from JSON if it's a raw string
                if '"response":' in summary:
                    from utils.parser import parse_llm_response
                    summary = parse_llm_response(summary).get("response", summary)
                return summary
            return raw_data

        elif intent == "vision":
            return analyze_screen(action or "What is briefly on this screen?")

        elif intent == "open_app":
            open_app(action, query=data.get("query"))

        elif intent == "play_music":
            play_music(action or "apple_music", query=data.get("query"))

        elif intent == "system_control":
            system_control(action)

        elif intent == "navigate":
            # Action is a URL or website name
            navigate_to(data.get("action") or "")

        elif intent == "search":
            search_web(action)

        elif intent == "weather":
            return get_weather(action or "auto")

        elif intent == "file_operation":
            if action == "downloads":
                open_downloads()
            elif action == "documents":
                open_documents()
            elif action == "desktop":
                open_desktop()
            elif action.startswith("find:"):
                filename = action[5:].strip()
                matches  = find_file(filename)
                return (f"Found {len(matches)} match(es). Opening folder location."
                        if matches else f"No file named '{filename}' found.")
            elif action.startswith("open:"):
                filename = action[5:].strip()
                if filename == "recent":
                    # Try to find the single most recent file in Downloads
                    import os
                    dl = os.path.join(os.path.expanduser("~"), "Downloads")
                    files = [os.path.join(dl, f) for f in os.listdir(dl) if os.path.isfile(os.path.join(dl, f))]
                    if not files: return "No files found to open."
                    latest = max(files, key=os.path.getctime)
                    os.startfile(latest)
                    return f"Opening most recent file: {os.path.basename(latest)}"
                else:
                    matches = find_file(filename)
                    if matches:
                        os.startfile(matches[0])
                        return f"Opening {os.path.basename(matches[0])}"
                    return f"I couldn't find a file named {filename}."

    except Exception as e:
        logging.error(f"Action execution error ({intent}/{action}): {e}")

    return None
