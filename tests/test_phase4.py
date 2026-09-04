import os
import sys
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ruby.os_control.app_launcher import AppLauncher, COMMON_APP_MAP
from ruby.os_control.file_ops import ScopedFileManager
from ruby.os_control.script_runner import ScriptRunner
from ruby.brain import RubyBrain
from ruby.tools.os_tools import (
    launch_app,
    read_memory_file,
    write_memory_file,
    delete_memory_file,
    execute_script
)


def test_app_launcher_mappings_and_processes():
    launcher = AppLauncher()
    assert "notepad" in COMMON_APP_MAP
    assert "calculator" in COMMON_APP_MAP
    assert "code" in COMMON_APP_MAP
    
    procs = launcher.list_running_processes()
    assert isinstance(procs, list)
    assert len(procs) > 0


def test_scoped_file_manager_lifecycle_and_security():
    fm = ScopedFileManager()
    
    # 1. Write file
    write_ok, write_msg = fm.write_file("test_scope_doc.txt", "Ruby Phase 4 Scoped Test")
    assert write_ok is True

    # 2. Read file
    read_ok, content = fm.read_file("test_scope_doc.txt")
    assert read_ok is True
    assert content == "Ruby Phase 4 Scoped Test"

    # 3. Security check: Path traversal attempt must be blocked
    bad_ok, bad_msg = fm.read_file("../../Windows/System32/drivers/etc/hosts")
    assert bad_ok is False
    assert "Security Violation" in bad_msg

    bad_write_ok, bad_write_msg = fm.write_file("../outside.txt", "hacked")
    assert bad_write_ok is False
    assert "Security Violation" in bad_write_msg

    # 4. Delete file
    del_ok, del_msg = fm.delete_file("test_scope_doc.txt")
    assert del_ok is True


def test_script_runner():
    sr = ScriptRunner()
    
    # Check script list
    scripts = sr.list_available_scripts()
    assert "system_status.py" in scripts

    # Run system_status.py
    ok, output = sr.run_script("system_status.py")
    assert ok is True
    assert "System Health Check" in output
    assert "CPU Usage" in output

    # Test destructive detection
    assert sr.is_potentially_destructive("Remove-Item -Recurse C:/") is True
    assert sr.is_potentially_destructive("del /f /q *") is True
    assert sr.is_potentially_destructive("print('hello')") is False


def test_brain_os_tools_registration():
    brain = RubyBrain()
    tool_names = [t["name"] for t in brain.tool_definitions]
    
    assert "launch_app" in tool_names
    assert "read_memory_file" in tool_names
    assert "write_memory_file" in tool_names
    assert "delete_memory_file" in tool_names
    assert "execute_script" in tool_names

    # Test tool dispatch in brain
    res = brain.execute_tool("write_memory_file", {
        "relative_path": "projects/os_test.md",
        "content": "Phase 4 OS integration verified."
    })
    assert "successfully" in res.lower()
