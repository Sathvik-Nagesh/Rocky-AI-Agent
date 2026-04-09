"""
True Autonomous Web Research.
Instead of dropping the user into a generic Google page, Rocky silently searches
the web, fetches the top article, reads the HTML, and returns the factual answer.
"""
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
import re

KEYWORDS = ["research", "deep search", "find out about", "explain completely", "what exactly is"]

def execute(query: str) -> str:
    # Extract the actual search query
    search_term = query
    for kw in KEYWORDS:
        search_term = search_term.replace(kw, "").strip()
    
    if not search_term:
        return "You said to research, but provided no topic. Clarify."

    print(f"[PLUGIN: Web Research] Finding data on: {search_term}")
    try:
        # Step 1: DuckDuckGo search to find the best link
        results = DDGS().text(search_term, max_results=3)
        if not results:
            return f"No data found for {search_term} on the web."

        best_link = results[0]["href"]
        print(f"[PLUGIN: Web Research] Best link found: {best_link}")

        # Step 2: Fetch the page
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(best_link, headers=headers, timeout=10)
        resp.raise_for_status()

        # Step 3: Extract the text using BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        paragraphs = soup.find_all('p')
        content = " ".join([p.get_text() for p in paragraphs[:5]])  # Top 5 paragraphs
        content = re.sub(r'\s+', ' ', content).strip()

        # Step 4: Summarize via local LLM so Rocky doesn't read 10 paragraphs aloud
        import sys
        import os
        jarvis_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jarvis")
        if jarvis_path not in sys.path:
            sys.path.insert(0, jarvis_path)
            
        from brain.llm import generate_response
        summary_prompt = f"Summarize this text concisely in 2 sentences max, as Rocky: {content[:2000]}"
        
        # We temporarily bypass history for a clean summary
        summary = generate_response(summary_prompt, history=[])
        import json
        try:
            # Parse the LLM's JSON to get the response string
            final = json.loads(summary)["response"]
            return final
        except:
            return "Web data retrieved. But processing failed. Try again."

    except Exception as e:
        print(f"[PLUGIN: Web Research] Error: {e}")
        return "I tried to research that, but encountered a network or processing error."
