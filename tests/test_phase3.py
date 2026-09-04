import os
import sys
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ruby.browser.browser_manager import BrowserManager, BROWSER_DATA_DIR, SCREENSHOTS_DIR
from ruby.browser.whatsapp import WhatsAppController
from ruby.brain import RubyBrain
from ruby.tools.browser_tools import (
    SEND_WHATSAPP_MESSAGE_TOOL,
    BROWSE_URL_TOOL,
    CAPTURE_SCREENSHOT_TOOL
)


def test_browser_directories():
    assert BROWSER_DATA_DIR.exists()
    assert SCREENSHOTS_DIR.exists()


def test_browser_manager_headless_navigation(tmp_path):
    bm = BrowserManager(headless=True, user_data_dir=tmp_path / "browser_test")
    try:
        ok, msg = bm.navigate("https://example.com")
        assert ok is True
        assert "example.com" in msg.lower() or "Example Domain" in msg

        # Test text extraction
        text_ok, text_content = bm.get_page_text()
        assert text_ok is True
        assert "Example Domain" in text_content

        # Test screenshot capture
        ss_ok, ss_path = bm.take_screenshot("test_phase3_sample.png")
        assert ss_ok is True
        assert Path(ss_path).exists()
    finally:
        bm.close()


def test_whatsapp_controller_instantiation(tmp_path):
    bm = BrowserManager(headless=True, user_data_dir=tmp_path / "wa_test")
    wa = WhatsAppController(browser_manager=bm)
    assert wa.browser is not None
    bm.close()


def test_brain_browser_tools_registration():
    brain = RubyBrain()
    tool_names = [t["name"] for t in brain.tool_definitions]
    
    assert "send_whatsapp_message" in tool_names
    assert "browse_url" in tool_names
    assert "capture_page_screenshot" in tool_names
    assert "web_search" in tool_names
    assert "remember_person" in tool_names
