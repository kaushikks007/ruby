import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Tuple, Optional, List
from ruby.config import DATA_ROOT

SCRIPTS_DIR = DATA_ROOT / "scripts"
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

DESTRUCTIVE_KEYWORDS = [
    "del ", "rmdir", "remove-item", "format ", "rm -rf", "drop database", "drop table", "truncate", "taskkill", "kill "
]


class ScriptRunner:
    """
    Executes scripts located in scripts/ or approved commands with safety checks.
    """
    def __init__(self):
        self.scripts_dir = SCRIPTS_DIR
        self.python_exec = DATA_ROOT / ".venv" / "Scripts" / "python.exe"
        if not self.python_exec.exists():
            self.python_exec = Path(sys.executable)

    def is_potentially_destructive(self, command_or_script: str) -> bool:
        lower = command_or_script.lower()
        for kw in DESTRUCTIVE_KEYWORDS:
            if kw in lower:
                return True
        return False

    def list_available_scripts(self) -> List[str]:
        return [f.name for f in self.scripts_dir.glob("*") if f.is_file()]

    def run_script(
        self,
        script_name: str,
        args: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> Tuple[bool, str]:
        """
        Executes a script in the scripts/ folder.
        """
        script_path = self.scripts_dir / script_name
        if not script_path.exists():
            # Check if user specified script with/without extension
            found = False
            for ext in [".py", ".ps1", ".bat", ".cmd", ".sh"]:
                candidate = self.scripts_dir / f"{script_name}{ext}"
                if candidate.exists():
                    script_path = candidate
                    found = True
                    break
            if not found:
                available = ", ".join(self.list_available_scripts()) or "none"
                return False, (
                    f"I couldn't find a script named '{script_name}' in '{self.scripts_dir}'. "
                    f"Available scripts: {available}."
                )

        suffix = script_path.suffix.lower()
        cmd: List[str] = []

        if suffix == ".py":
            cmd = [str(self.python_exec), str(script_path)]
        elif suffix == ".ps1":
            cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
        elif suffix in [".bat", ".cmd"]:
            cmd = ["cmd.exe", "/c", str(script_path)]
        else:
            cmd = [str(script_path)]

        if args:
            cmd.extend(args.split())

        try:
            start_time = time.time()
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=str(DATA_ROOT)
            )
            elapsed = round(time.time() - start_time, 2)
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            if proc.returncode == 0:
                output = stdout if stdout else "(Script completed with no console output)"
                return True, f"Script '{script_path.name}' finished successfully in {elapsed}s:\n\n{output}"
            else:
                err_msg = stderr if stderr else stdout
                return False, (
                    f"Script '{script_path.name}' failed with exit code {proc.returncode} ({elapsed}s):\n"
                    f"{err_msg}"
                )

        except subprocess.TimeoutExpired:
            return False, f"Script '{script_path.name}' timed out after {timeout_seconds} seconds."
        except Exception as e:
            return False, f"Could not execute script '{script_path.name}': {str(e)}"
