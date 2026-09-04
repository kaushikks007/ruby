import os
import sys
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ruby.config import MEMORY_DIR, PROFILE_PATH, DAILY_LOG_DIR, PROJECTS_DIR
from ruby.memory_manager import MemoryManager
from ruby.tools.web_search import search_web, fetch_webpage, WEB_SEARCH_TOOL_DEFINITION
from ruby.tools.memory_tools import (
    remember_person,
    update_user_preference,
    save_project_update,
    log_daily_event,
)
from ruby.brain import RubyBrain


def test_directories_exist():
    assert MEMORY_DIR.exists()
    assert DAILY_LOG_DIR.exists()
    assert PROJECTS_DIR.exists()


def test_memory_profile_lifecycle():
    mm = MemoryManager()
    profile = mm.load_profile()
    assert "user" in profile
    assert profile["user"]["name"] == "kaushik"

    # Test update
    mm.update_profile("user", "role", "Lead Engineer")
    updated = mm.load_profile()
    assert updated["user"]["role"] == "Lead Engineer"

    # Test add known person
    mm.add_known_person("Arjun", "Friend & Co-builder", "Working on AI projects together")
    updated = mm.load_profile()
    known = [p for p in updated["user"]["known_people"] if p["name"] == "Arjun"]
    assert len(known) == 1
    assert known[0]["relationship"] == "Friend & Co-builder"

    # Test add routine
    mm.add_routine("Morning chai and status check at 9 AM")
    updated = mm.load_profile()
    assert "Morning chai and status check at 9 AM" in updated["user"]["routines"]


def test_daily_log_and_projects():
    mm = MemoryManager()
    
    # Daily log
    log_file = mm.save_daily_log("Tested Ruby brain architecture and memory systems.", tags=["test", "phase1"])
    assert log_file.exists()
    
    logs = mm.get_recent_daily_logs(days=1)
    assert len(logs) >= 1
    assert "Tested Ruby brain" in logs[0]["content"]

    # Projects
    proj_file = mm.append_project_note("ruby_assistant", "Phase 1 Brain setup completed.")
    assert proj_file.exists()
    
    projects = mm.get_all_projects()
    assert "ruby_assistant" in projects
    assert "Phase 1 Brain setup completed." in projects["ruby_assistant"]


def test_memory_context_builder():
    mm = MemoryManager()
    context = mm.build_memory_context()
    assert "kaushik" in context
    assert "CURRENT USER & MEMORY CONTEXT" in context


def test_web_search_tool():
    # Test searching for something current
    results = search_web("Python programming language release news", max_results=3)
    assert isinstance(results, str)
    assert len(results) > 20
    assert "Python" in results or "results for" in results


def test_ruby_brain_initialization_and_system_prompt():
    brain = RubyBrain()
    assert brain.memory_mgr is not None
    prompt = brain.assemble_system_prompt()
    assert "You are Ruby, a personal AI assistant" in prompt
    assert "kaushik" in prompt
    assert len(brain.tool_definitions) >= 4


def test_ruby_brain_tool_dispatch():
    brain = RubyBrain()
    
    # Test dispatching memory tool
    res = brain.execute_tool("remember_person", {
        "name": "Sarah",
        "relationship": "Colleague",
        "notes": "Designs 3D UI assets"
    })
    assert "Successfully saved" in res

    # Verify in profile
    profile = brain.memory_mgr.load_profile()
    sarah = [p for p in profile["user"]["known_people"] if p["name"] == "Sarah"]
    assert len(sarah) == 1
