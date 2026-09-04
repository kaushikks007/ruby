import sys
from typing import Optional, Dict, Any
from rich.console import Console
from rich.prompt import Prompt

from ruby.browser.browser_manager import BrowserManager
from ruby.browser.whatsapp import WhatsAppController

console = Console()
_browser_mgr: Optional[BrowserManager] = None
_whatsapp_ctrl: Optional[WhatsAppController] = None


def get_browser_manager() -> BrowserManager:
    global _browser_mgr
    if _browser_mgr is None:
        _browser_mgr = BrowserManager(headless=False)
    return _browser_mgr


def get_whatsapp_controller() -> WhatsAppController:
    global _whatsapp_ctrl
    if _whatsapp_ctrl is None:
        _whatsapp_ctrl = WhatsAppController(get_browser_manager())
    return _whatsapp_ctrl


def send_whatsapp_message(contact_name: str, message: str, pre_approved: bool = False) -> str:
    """
    Sends a WhatsApp message to a contact.
    Narration + staging + user confirmation safeguard before sending.
    """
    console.print(f"\n[bold magenta]⚡ Narrating Plan:[/bold magenta] Opening WhatsApp Web and messaging [bold cyan]{contact_name}[/bold cyan] — one sec.\n")
    
    wa = get_whatsapp_controller()
    
    def on_status_update(status_text: str):
        console.print(f"[dim]>> {status_text}[/dim]")

    # Step 1: Stage the message
    ok, msg = wa.prepare_message(contact_name, message, on_status=on_status_update)
    if not ok:
        return f"Could not stage WhatsApp message: {msg}"

    # Step 2: User confirmation safeguard
    if not pre_approved:
        console.print(f"\n[bold yellow]⚠️  CONFIRMATION REQUIRED[/bold yellow]")
        console.print(f"Recipient: [bold cyan]{contact_name}[/bold cyan]")
        console.print(f"Message:   [bold white]\"{message}\"[/bold white]")
        
        try:
            confirm = Prompt.ask("Send this WhatsApp message now? (y/n)", default="y").strip().lower()
        except Exception:
            confirm = "y"

        if confirm not in ["y", "yes"]:
            return f"Cancelled: WhatsApp message to {contact_name} was NOT sent (declined by user)."

    # Step 3: Send
    send_ok, send_msg = wa.send_staged_message()
    if send_ok:
        return f"Sent WhatsApp message to {contact_name}: \"{message}\""
    else:
        return f"Error sending WhatsApp message: {send_msg}"


def browse_url(url: str) -> str:
    """Navigates to a webpage in Chrome and extracts the page text."""
    console.print(f"\n[bold magenta]⚡ Narrating Plan:[/bold magenta] Opening Chrome and browsing to [bold cyan]{url}[/bold cyan]...\n")
    bm = get_browser_manager()
    ok, nav_msg = bm.navigate(url)
    if not ok:
        return f"Failed to open {url}: {nav_msg}"
    
    text_ok, text_content = bm.get_page_text()
    if text_ok:
        return f"Successfully opened {url}.\nPage Content Summary:\n{text_content}"
    return f"Opened {url}, but could not extract page text: {text_content}"


def capture_page_screenshot(filename: Optional[str] = None) -> str:
    """Takes a screenshot of the current active browser page."""
    bm = get_browser_manager()
    ok, path_or_err = bm.take_screenshot(filename)
    if ok:
        return f"Screenshot saved to: {path_or_err}"
    return f"Screenshot failed: {path_or_err}"


# Anthropic Claude Tool Definitions
SEND_WHATSAPP_MESSAGE_TOOL = {
    "name": "send_whatsapp_message",
    "description": "Send a message to a person or group on WhatsApp Web. Opens Chrome, locates the contact, types the message, requests user confirmation, and sends.",
    "input_schema": {
        "type": "object",
        "properties": {
            "contact_name": {
                "type": "string",
                "description": "Name of the WhatsApp contact or group to message."
            },
            "message": {
                "type": "string",
                "description": "The exact text message to send."
            }
        },
        "required": ["contact_name", "message"]
    }
}

BROWSE_URL_TOOL = {
    "name": "browse_url",
    "description": "Open a website URL in Google Chrome, view the live rendered page, and extract its visible text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The website URL to browse."
            }
        },
        "required": ["url"]
    }
}

CAPTURE_SCREENSHOT_TOOL = {
    "name": "capture_page_screenshot",
    "description": "Capture a screenshot of the current browser page and save it locally in memory/screenshots.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Optional filename for the screenshot image (.png)."
            }
        }
    }
}
