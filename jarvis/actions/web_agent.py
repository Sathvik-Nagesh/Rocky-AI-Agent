"""
Autonomous Web Agent powered by Playwright.
Allows Rocky to browse the web, extract deep content, and perform browser-based tasks.
"""
import os
import logging
import asyncio
from playwright.sync_api import sync_playwright
try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None

def run_web_task(query: str, url: str = None) -> str:
    """
    Search for a query or visit a URL, extract main content, and return a summary.
    If no URL is provided, it uses DuckDuckGo to find one first.
    """
    if not url and not query:
        return "No website or search query provided."

    results = ""
    try:
        with sync_playwright() as p:
            # We use Chromium for best compatibility
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            if stealth_sync:
                stealth_sync(page)

            target_url = url
            if not target_url:
                # Use DuckDuckGo to find the best link
                search_url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
                print(f"[WEB AGENT] Researching: {query}")
                page.goto(search_url, wait_until="networkidle")
                # Pick the first actual result link
                first_link = page.get_by_css_selector(".result__a").first
                if first_link:
                    target_url = first_link.get_attribute("href")
                else:
                    return f"I couldn't find any results for '{query}' on the web."

            print(f"[WEB AGENT] Visiting: {target_url}")
            page.goto(target_url, wait_until="networkidle", timeout=30000)
            
            # Extract main text content
            # We try to target 'article' or 'main' first, then body
            page.wait_for_timeout(1000) # Give it a second to render JS
            
            body_text = page.inner_text("body")
            
            # Take a small snippet (first 3000 chars) to avoid LLM context explosion
            snippet = body_text[:4000].strip()
            
            browser.close()
            
            if not snippet:
                return f"I reached {target_url} but the page appeared empty or blocked by a bot-check."

            return f"Data extracted from {target_url}: {snippet}"

    except Exception as e:
        logging.error(f"Web Agent Error: {e}")
        return f"I encountered an error while browsing: {str(e)}"

def run_mercenary_swarm(query: str) -> str:
    """Spawn multiple parallel agents to gather deep intelligence."""
    print(f"[SWARM] Deploying 3 Mercenary Agents for: {query}")
    
    # We'll use a simple ThreadPool to run run_web_task in parallel
    from concurrent.futures import ThreadPoolExecutor
    
    # First, get a list of search result links from DuckDuckGo
    search_links = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            search_url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
            page.goto(search_url)
            # Extract first 3 results
            links = page.locator(".result__a").all()[:3]
            search_links = [l.get_attribute("href") for l in links if l.get_attribute("href")]
            browser.close()
    except Exception as e:
        return f"Swarm initialization failed: {e}"

    if not search_links:
        return run_web_task(query) # Fallback to single agent

    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Each agent visits one of the top links
        futures = [executor.submit(run_web_task, query, link) for link in search_links]
        for f in futures:
            results.append(f.result())

    combined = "\n---\n".join(results)
    return f"Intelligence gathered from {len(results)} sources:\n{combined}"

if __name__ == "__main__":
    # Test
    print(run_web_task("latest spaceX launch news"))
