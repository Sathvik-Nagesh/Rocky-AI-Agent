"""Weather fetch using wttr.in — no API key required."""
import requests
import logging

def get_weather(location: str = "auto") -> str:
    """Returns a one-line weather description for the given location."""
    try:
        # wttr.in format=3 gives "City: 🌤 +25°C" but without emoji use format=j1 JSON
        url = f"https://wttr.in/{location}?format=j1"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()

        current = data["current_condition"][0]
        feels_c = current["FeelsLikeC"]
        desc    = current["weatherDesc"][0]["value"]
        area    = data["nearest_area"][0]["areaName"][0]["value"]
        country = data["nearest_area"][0]["country"][0]["value"]

        return f"{area}, {country}: {desc}, feels like {feels_c} degrees Celsius."
    except Exception as e:
        logging.error(f"Weather fetch failed: {e}")
        return "Weather data unavailable at the moment."
