import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from ruby.config import DATA_ROOT

try:
    from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright
except ImportError:
    sync_playwright = None
    BrowserContext = None
    Page = None
    Playwright = None

BROWSER_DATA_DIR = DATA_ROOT / "browser_data"
SCREENSHOTS_DIR = DATA_ROOT / "memory" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)


class BrowserManager:
    """
    Manages Playwright browser instance with persistent session data in browser_data/.
    Uses local Google Chrome or Microsoft Edge.
    """
    def __init__(self, headless: bool = False, user_data_dir: Optional[Path] = None):
        self.headless = headless
        self.user_data_dir = user_data_dir or BROWSER_DATA_DIR
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def _ensure_browser(self) -> Tuple[bool, str]:
        if sync_playwright is None:
            return False, "Playwright is not installed in the environment."

        if self.context is not None and self.page is not None:
            try:
                # Test if page is alive
                self.page.title()
                return True, "Browser active"
            except Exception:
                self.close()

        try:
            self.playwright = sync_playwright().start()
            
            # Determine channel: chrome -> msedge -> default chromium
            channel = "chrome"
            chrome_path = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
            if not chrome_path.exists():
                channel = "msedge"

            Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                channel=channel,
                headless=self.headless,
                viewport={"width": 1280, "height": 800},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized"
                ],
                no_viewport=True if not self.headless else False
            )

            pages = self.context.pages
            if pages:
                self.page = pages[0]
            else:
                self.page = self.context.new_page()

            return True, f"Browser started successfully using {channel}."
        except Exception as e:
            self.close()
            return False, f"Failed to open browser: {str(e)}"

    def navigate(self, url: str, timeout: int = 30000) -> Tuple[bool, str]:
        """Navigate to a URL and return status."""
        ok, msg = self._ensure_browser()
        if not ok:
            return False, msg

        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            title = self.page.title()
            return True, f"Navigated to '{url}' (Page Title: {title})"
        except Exception as e:
            return False, f"Could not load {url}: {str(e)}"

    def get_page_text(self, max_chars: int = 4000) -> Tuple[bool, str]:
        """Extract visible text from current page."""
        ok, msg = self._ensure_browser()
        if not ok:
            return False, msg

        try:
            text = self.page.inner_text("body")
            clean = " ".join(text.split())
            if len(clean) > max_chars:
                clean = clean[:max_chars] + "... [truncated]"
            return True, clean
        except Exception as e:
            return False, f"Failed to extract page text: {str(e)}"

    def take_screenshot(self, filename: Optional[str] = None) -> Tuple[bool, str]:
        """Takes a screenshot of the current page and saves to memory/screenshots/."""
        ok, msg = self._ensure_browser()
        if not ok:
            return False, msg

        try:
            if not filename:
                filename = f"screenshot_{int(time.time())}.png"
            elif not filename.endswith(".png"):
                filename += ".png"

            filepath = SCREENSHOTS_DIR / filename
            self.page.screenshot(path=str(filepath), full_page=False)
            return True, str(filepath)
        except Exception as e:
            return False, f"Failed to take screenshot: {str(e)}"

    def close(self):
        """Closes browser context and Playwright driver."""
        try:
            if self.context:
                self.context.close()
                self.context = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
            self.page = None
        except Exception:
            pass
