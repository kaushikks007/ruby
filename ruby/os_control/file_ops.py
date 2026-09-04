import os
from pathlib import Path
from typing import Tuple, List, Optional
from ruby.config import MEMORY_DIR


class ScopedFileManager:
    """
    Safely reads, writes, and manages files strictly scoped to the memory directory.
    Prevents path traversal and enforces safeguards on destructive actions.
    """
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = (base_dir or MEMORY_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Tuple[Optional[Path], Optional[str]]:
        """
        Resolves path and guarantees it stays inside self.base_dir.
        """
        # Clean leading slashes
        clean_rel = relative_path.lstrip("/\\")
        target = (self.base_dir / clean_rel).resolve()

        try:
            target.relative_to(self.base_dir)
        except ValueError:
            return None, f"Security Violation: Access outside memory directory '{self.base_dir}' is blocked."

        return target, None

    def read_file(self, relative_path: str, max_chars: int = 10000) -> Tuple[bool, str]:
        target, err = self._resolve_safe_path(relative_path)
        if err:
            return False, err

        if not target.exists():
            return False, f"File '{relative_path}' was not found in memory folder."
        if not target.is_file():
            return False, f"'{relative_path}' is a directory, not a file."

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)
            return True, content
        except Exception as e:
            return False, f"Failed to read '{relative_path}': {str(e)}"

    def write_file(self, relative_path: str, content: str, append: bool = False) -> Tuple[bool, str]:
        target, err = self._resolve_safe_path(relative_path)
        if err:
            return False, err

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(target, mode, encoding="utf-8") as f:
                f.write(content)
            action = "Appended to" if append else "Wrote"
            return True, f"{action} memory file '{target.name}' successfully."
        except Exception as e:
            return False, f"Failed to write file '{relative_path}': {str(e)}"

    def delete_file(self, relative_path: str) -> Tuple[bool, str]:
        target, err = self._resolve_safe_path(relative_path)
        if err:
            return False, err

        if not target.exists():
            return False, f"Cannot delete: File '{relative_path}' does not exist in memory."

        try:
            if target.is_file():
                target.unlink()
                return True, f"Deleted memory file '{relative_path}'."
            elif target.is_dir():
                import shutil
                shutil.rmtree(target)
                return True, f"Deleted directory '{relative_path}'."
            return False, "Unknown file type."
        except Exception as e:
            return False, f"Failed to delete '{relative_path}': {str(e)}"

    def list_files(self, subfolder: str = "") -> List[str]:
        target, err = self._resolve_safe_path(subfolder)
        if err or not target.exists() or not target.is_dir():
            return []

        results = []
        for item in target.rglob("*"):
            if item.is_file():
                rel = item.relative_to(self.base_dir)
                results.append(str(rel))
        return results
