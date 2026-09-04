import time
from typing import Tuple, Optional, Callable
from ruby.browser.browser_manager import BrowserManager


class WhatsAppController:
    """
    Automates WhatsApp Web messaging with Playwright.
    Enforces a strict confirmation-before-send safeguard and provides plain-language error reporting.
    """
    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        self.browser = browser_manager or BrowserManager(headless=False)

    def prepare_message(
        self,
        contact_name: str,
        message: str,
        on_status: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """
        Step 1: Opens WhatsApp Web, searches for contact, selects chat, and stages message in text box.
        Does NOT hit send yet.
        """
        def notify(msg: str):
            if on_status:
                on_status(msg)
            else:
                print(f"[WhatsApp] {msg}")

        notify("Opening WhatsApp Web in Chrome...")
        ok, msg = self.browser.navigate("https://web.whatsapp.com", timeout=45000)
        if not ok:
            return False, f"Could not reach WhatsApp Web: {msg}. Please check your internet connection."

        page = self.browser.page
        if not page:
            return False, "Browser page is not available."

        # Check for QR code login screen
        notify("Checking login status...")
        try:
            # Wait up to 10 seconds for either chat list or QR code canvas
            page.wait_for_selector(
                "div[contenteditable='true'], canvas, [data-icon='chat']",
                timeout=12000
            )
        except Exception:
            pass

        # Check if QR code is present
        qr_elem = page.query_selector("canvas, [data-testid='qrcode']")
        if qr_elem:
            return False, (
                "WhatsApp Web requires a one-time QR code login. "
                "Please scan the QR code on your screen using your phone's WhatsApp (Linked Devices), "
                "then try again once logged in."
            )

        # Look for search bar to find contact
        notify(f"Searching for contact '{contact_name}'...")
        search_selectors = [
            "div[contenteditable='true'][data-tab='3']",
            "div[role='textbox'][data-tab='3']",
            "div[contenteditable='true'][title*='Search']",
            "div[contenteditable='true']",
            "input[placeholder*='Search']"
        ]

        search_box = None
        for sel in search_selectors:
            try:
                search_box = page.wait_for_selector(sel, timeout=5000)
                if search_box and search_box.is_visible():
                    break
            except Exception:
                continue

        if not search_box:
            return False, (
                "I couldn't locate the chat search bar on WhatsApp Web. "
                "The page may still be loading, or WhatsApp updated its layout. "
                "Please make sure WhatsApp Web is completely loaded."
            )

        try:
            search_box.click()
            search_box.fill("")
            time.sleep(0.3)
            # Type contact name
            search_box.fill(contact_name)
            time.sleep(1.5)  # Wait for search results list to populate
        except Exception as e:
            return False, f"Failed to type contact name in search: {str(e)}"

        # Find contact in search results
        notify(f"Looking for '{contact_name}' in search results...")
        contact_found = False
        
        # Try matching by title, text, or first search item
        contact_selectors = [
            f"span[title='{contact_name}']",
            f"span[title*='{contact_name}']",
            f"div[role='listitem'] span:has-text('{contact_name}')",
            "div[role='listitem']",
            "div[tabindex='-1'][role='gridcell']"
        ]

        for sel in contact_selectors:
            try:
                elem = page.query_selector(sel)
                if elem and elem.is_visible():
                    elem.click()
                    contact_found = True
                    time.sleep(1.0)
                    break
            except Exception:
                continue

        if not contact_found:
            # Fallback: Press Enter on the search box to pick top result
            try:
                page.keyboard.press("Enter")
                time.sleep(1.0)
                contact_found = True
            except Exception:
                pass

        # Check if chat conversation is open by locating message input box
        notify("Locating message input field...")
        message_input_selectors = [
            "div[contenteditable='true'][data-tab='10']",
            "footer div[contenteditable='true']",
            "div[role='textbox'][spellcheck='true']",
            "div[contenteditable='true'][title*='Type a message']"
        ]

        msg_box = None
        for sel in message_input_selectors:
            try:
                msg_box = page.wait_for_selector(sel, timeout=6000)
                if msg_box and msg_box.is_visible():
                    break
            except Exception:
                continue

        if not msg_box:
            return False, (
                f"I couldn't open the chat for '{contact_name}'. "
                f"It's possible the contact doesn't exist in your WhatsApp contacts, or the name is spelled differently."
            )

        # Stage the message in the input box
        try:
            msg_box.click()
            msg_box.fill(message)
            time.sleep(0.5)
            notify(f"Message staged in text box for '{contact_name}'.")
            return True, f"Message staged for '{contact_name}': \"{message}\""
        except Exception as e:
            return False, f"Failed to type message into chat box: {str(e)}"

    def send_staged_message(self) -> Tuple[bool, str]:
        """
        Step 2: Hits Send (Enter / Click send button) after user confirmation.
        """
        page = self.browser.page
        if not page:
            return False, "Browser is not open."

        try:
            # Press enter to send
            page.keyboard.press("Enter")
            time.sleep(1.0)
            
            # Check if send button can be clicked as fallback
            send_btn = page.query_selector("button[data-tab='11'], span[data-icon='send'], span[data-icon='send-refreshed']")
            if send_btn and send_btn.is_visible():
                send_btn.click()
                time.sleep(1.0)

            return True, "WhatsApp message sent successfully."
        except Exception as e:
            return False, f"Failed to hit send: {str(e)}"
