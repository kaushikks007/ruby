import json
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List
import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web for up-to-date information, news, current events, prices, or facts.
    """
    results = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Attempt 1: DDGS Python package
    if DDGS is not None:
        try:
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=max_results))
                if ddg_results:
                    for r in ddg_results:
                        results.append({
                            "title": r.get("title", ""),
                            "snippet": r.get("body", ""),
                            "url": r.get("href", "")
                        })
        except Exception as e:
            # Fall back to alternative scraping or DuckDuckGo HTML
            pass

    # Attempt 2: Direct DuckDuckGo HTML search if DDGS package failed
    if not results:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(
                f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for result in soup.find_all("div", class_="result")[:max_results]:
                    title_elem = result.find("a", class_="result__a")
                    snippet_elem = result.find("a", class_="result__snippet")
                    if title_elem and snippet_elem:
                        url = title_elem.get("href", "")
                        # Parse out actual URL from ddg redirect if needed
                        if "uddg=" in url:
                            try:
                                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                                url = parsed.get("uddg", [url])[0]
                            except Exception:
                                pass
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "snippet": snippet_elem.get_text(strip=True),
                            "url": url
                        })
        except Exception as e:
            pass

    if not results:
        return f"Web search for '{query}' returned no results or failed to connect. (Current time: {timestamp})"

    output = [f"Web search results for: '{query}' [Timestamp: {timestamp}]\n"]
    for i, r in enumerate(results, 1):
        output.append(f"{i}. **{r['title']}**\n   {r['snippet']}\n   Source: {r['url']}")
    
    return "\n\n".join(output)


def fetch_webpage(url: str, max_chars: int = 3000) -> str:
    """
    Fetch and extract clean readable text from a specific webpage URL.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
            
        text = soup.get_text(separator=" ", strip=True)
        # Clean up whitespace
        text = " ".join(text.split())
        
        if len(text) > max_chars:
            text = text[:max_chars] + "... [content truncated]"
            
        return f"Content extracted from {url}:\n\n{text}"
    except Exception as e:
        return f"Failed to fetch content from {url}: {str(e)}"


# Anthropic Claude Tool Definitions
WEB_SEARCH_TOOL_DEFINITION = {
    "name": "web_search",
    "description": "Search the live web for current events, news, stock prices, scores, weather, product details, or recent developments.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up on the web."
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to retrieve (default: 5).",
                "default": 5
            }
        },
        "required": ["query"]
    }
}

FETCH_WEBPAGE_TOOL_DEFINITION = {
    "name": "fetch_webpage",
    "description": "Fetch and extract readable text from a specific URL when more depth is needed after a search.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full HTTP/HTTPS URL to fetch."
            }
        },
        "required": ["url"]
    }
}
