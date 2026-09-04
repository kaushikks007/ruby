import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Tuple, Optional, Dict, List, Any
import psutil

# Standard Windows application shortcuts and executable targets
COMMON_APP_MAP: Dict[str, List[str]] = {
    "notepad": ["notepad.exe", "notepad"],
    "calculator": ["calc.exe", "calc"],
    "calc": ["calc.exe", "calc"],
    "vscode": ["code.cmd", "code.exe", "code"],
    "code": ["code.cmd", "code.exe", "code"],
    "chrome": [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "chrome.exe", "chrome"
    ],
    "edge": [
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        "msedge.exe", "msedge"
    ],
    "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
    "powershell": ["powershell.exe"],
    "cmd": ["cmd.exe"],
    "spotify": [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        "spotify.exe", "spotify:"
    ],
    "explorer": ["explorer.exe"],
    "files": ["explorer.exe"],
    "taskmgr": ["taskmgr.exe"],
    "settings": ["ms-settings:"],
}


class AppLauncher:
    """
    Launches and manages Windows desktop applications with plain-English feedback.
    """
    def __init__(self):
        pass

    def launch(self, app_name: str, args: Optional[str] = None) -> Tuple[bool, str]:
        app_key = app_name.lower().strip()
        candidates = COMMON_APP_MAP.get(app_key, [app_name])
        
        target_exec = None
        is_uri_scheme = False

        for candidate in candidates:
            # Check for URI schemes (e.g., ms-settings:, spotify:)
            if candidate.endswith(":") or "://" in candidate:
                target_exec = candidate
                is_uri_scheme = True
                break
            
            # Check direct file path
            candidate_path = Path(candidate)
            if candidate_path.exists():
                target_exec = str(candidate_path)
                break
            
            # Check on system PATH
            found = shutil.which(candidate)
            if found:
                target_exec = found
                break

        if not target_exec:
            # Try launching by generic name via startfile or shell
            target_exec = app_name

        try:
            if is_uri_scheme:
                os.startfile(target_exec)
                return True, f"Launched '{app_name}' via Windows protocol ({target_exec})."

            cmd = [target_exec]
            if args:
                cmd.extend(args.split())

            # Spawn process detached without blocking Python loop
            proc = subprocess.Popen(
                cmd,
                shell=True if not Path(target_exec).exists() else False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            )
            time.sleep(0.5)

            return True, f"Successfully launched '{app_name}' (PID: {proc.pid})."
        except FileNotFoundError:
            return False, (
                f"I couldn't find the application '{app_name}' on your PC. "
                "Make sure it is installed or try specifying its full path."
            )
        except Exception as e:
            return False, f"Failed to launch '{app_name}': {str(e)}"

    def list_running_processes(self, filter_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists running GUI application processes on the PC."""
        results = []
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                name = proc.info['name'] or ""
                if filter_name and filter_name.lower() not in name.lower():
                    continue
                results.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return results[:30]
