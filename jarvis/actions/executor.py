"""
Action executor — routes parsed intent to the correct action function.
"""
import logging
from actions.system import (
    open_app, play_music, system_control, search_web, navigate_to,
    open_downloads, open_documents, open_desktop, find_file, WEBSITE_MAP,
)
from actions.weather import get_weather

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
        if intent == "open_app":
            open_app(action)

        elif intent == "play_music":
            play_music(action or "apple_music")

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

    except Exception as e:
        logging.error(f"Action execution error ({intent}/{action}): {e}")

    return None
