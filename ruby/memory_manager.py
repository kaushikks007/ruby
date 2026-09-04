import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from ruby.config import (
    PROFILE_PATH,
    DAILY_LOG_DIR,
    PROJECTS_DIR,
    MEMORY_DIR,
)

DEFAULT_PROFILE = {
    "user": {
        "name": "kaushik",
        "role": "Owner / Developer",
        "timezone": "Asia/Kolkata",
        "preferences": {
            "communication_style": "direct, warm, concise, like a smart friend over chai",
            "voice_enabled": False,
            "hackathon_mode": False
        },
        "routines": [],
        "known_people": [],
        "notes": "Always-on companion. Checks in naturally on stress, deadlines, and projects."
    },
    "assistant": {
        "name": "Ruby",
        "role": "Personal AI Assistant & Companion",
        "version": "0.1.0",
        "voice_choice": "default",
        "wake_word": "Hey Ruby"
    }
}


class MemoryManager:
    def __init__(self):
        self._ensure_files()

    def _ensure_files(self):
        if not PROFILE_PATH.exists():
            self.save_profile(DEFAULT_PROFILE)

    def load_profile(self) -> Dict[str, Any]:
        try:
            if PROFILE_PATH.exists():
                with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[MemoryManager] Error loading profile: {e}")
        return DEFAULT_PROFILE.copy()

    def save_profile(self, profile_data: Dict[str, Any]) -> bool:
        try:
            with open(PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[MemoryManager] Error saving profile: {e}")
            return False

    def update_profile(self, section: str, key: str, value: Any) -> bool:
        profile = self.load_profile()
        if section not in profile:
            profile[section] = {}
        if isinstance(profile[section], dict):
            profile[section][key] = value
        else:
            profile[section] = {key: value}
        return self.save_profile(profile)

    def add_known_person(self, name: str, relationship: str = "", notes: str = "") -> bool:
        profile = self.load_profile()
        known_people = profile.get("user", {}).get("known_people", [])
        
        # Check if person already exists, update if so
        updated = False
        for p in known_people:
            if p.get("name", "").lower() == name.lower():
                if relationship:
                    p["relationship"] = relationship
                if notes:
                    p["notes"] = notes
                p["last_updated"] = datetime.now().isoformat()
                updated = True
                break
        if not updated:
            known_people.append({
                "name": name,
                "relationship": relationship,
                "notes": notes,
                "last_updated": datetime.now().isoformat()
            })
            
        profile.setdefault("user", {})["known_people"] = known_people
        return self.save_profile(profile)

    def add_routine(self, routine_text: str) -> bool:
        profile = self.load_profile()
        routines = profile.get("user", {}).get("routines", [])
        if routine_text not in routines:
            routines.append(routine_text)
            profile.setdefault("user", {})["routines"] = routines
            return self.save_profile(profile)
        return True

    # Daily Log Management
    def save_daily_log(self, summary: str, log_date: Optional[str] = None, tags: Optional[List[str]] = None) -> Path:
        if not log_date:
            log_date = datetime.now().strftime("%Y-%m-%d")
        
        log_file = DAILY_LOG_DIR / f"{log_date}.md"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        tag_str = f" [Tags: {', '.join(tags)}]" if tags else ""
        entry = f"\n### [{timestamp}]{tag_str}\n{summary.strip()}\n"
        
        if not log_file.exists():
            header = f"# Daily Log — {log_date}\n"
            content = header + entry
        else:
            content = entry

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(content)
            
        return log_file

    def get_recent_daily_logs(self, days: int = 5) -> List[Dict[str, str]]:
        results = []
        today = date.today()
        for i in range(days):
            day_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            log_file = DAILY_LOG_DIR / f"{day_str}.md"
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        results.append({
                            "date": day_str,
                            "content": f.read().strip()
                        })
                except Exception as e:
                    print(f"[MemoryManager] Error reading log {day_str}: {e}")
        return results

    # Projects Management
    def save_project_doc(self, project_name: str, content: str) -> Path:
        filename = f"{project_name.lower().replace(' ', '_')}.md"
        project_file = PROJECTS_DIR / filename
        with open(project_file, "w", encoding="utf-8") as f:
            f.write(content)
        return project_file

    def append_project_note(self, project_name: str, note: str) -> Path:
        filename = f"{project_name.lower().replace(' ', '_')}.md"
        project_file = PROJECTS_DIR / filename
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n- **[{timestamp}]**: {note.strip()}\n"
        
        if not project_file.exists():
            content = f"# Project: {project_name}\n\n## Notes & Milestones\n" + entry
            with open(project_file, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(project_file, "a", encoding="utf-8") as f:
                f.write(entry)
        return project_file

    def get_all_projects(self) -> Dict[str, str]:
        projects = {}
        for p in PROJECTS_DIR.glob("*.md"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    projects[p.stem] = f.read().strip()
            except Exception as e:
                print(f"[MemoryManager] Error reading project {p}: {e}")
        return projects

    # Dynamic context builder for LLM
    def build_memory_context(self, max_context_chars: int = 8000) -> str:
        profile = self.load_profile()
        user_info = profile.get("user", {})
        known_people = user_info.get("known_people", [])
        routines = user_info.get("routines", [])

        parts = ["\n--- CURRENT USER & MEMORY CONTEXT ---"]
        parts.append(f"User: {user_info.get('name', 'kaushik')}")
        if user_info.get('role'):
            parts.append(f"Role: {user_info.get('role')}")
        if user_info.get('preferences'):
            parts.append(f"Preferences: {json.dumps(user_info.get('preferences'))}")
        if routines:
            parts.append(f"Known Routines: {', '.join(routines)}")
        if known_people:
            ppl_list = [f"{p.get('name')} ({p.get('relationship', 'contact')}: {p.get('notes', '')})" for p in known_people]
            parts.append(f"People in kaushik's life: {'; '.join(ppl_list)}")

        # Recent logs — only include the last 3 days to keep context lightweight
        recent_logs = self.get_recent_daily_logs(days=3)
        if recent_logs:
            parts.append("\nRecent Daily Log Context (past few days):")
            for log in recent_logs:
                # Truncate very long daily logs to keep context bounded
                content = log['content']
                if len(content) > 1500:
                    content = content[:1500] + "... [truncated, full log on disk]"
                parts.append(f"[{log['date']}]\n{content}")

        # Active projects
        projects = self.get_all_projects()
        if projects:
            parts.append("\nActive Projects & Deadlines:")
            for name, content in projects.items():
                # Cap individual project context
                if len(content) > 2000:
                    content = content[:2000] + "... [truncated]"
                parts.append(f"=== Project: {name} ===\n{content}")

        parts.append("--- END MEMORY CONTEXT ---\n")
        full = "\n".join(parts)

        # Hard cap: if total context exceeds the limit, trim from the tail
        if len(full) > max_context_chars:
            full = full[:max_context_chars] + "\n[context truncated to fit token limit]"

        return full

    def cleanup_old_logs(self, keep_days: int = 30) -> int:
        """Delete daily log files older than keep_days. Returns count of removed files.
        This keeps the daily_log/ folder from growing unbounded over months of use."""
        cutoff = date.today() - timedelta(days=keep_days)
        removed = 0
        for log_file in DAILY_LOG_DIR.glob("*.md"):
            try:
                file_date = datetime.strptime(log_file.stem, "%Y-%m-%d").date()
                if file_date < cutoff:
                    log_file.unlink()
                    removed += 1
            except (ValueError, OSError):
                continue
        return removed

    def summarize_old_entries(self, older_than_days: int = 7) -> int:
        """Collapse multi-entry daily logs older than older_than_days into single-line summaries.
        Each timestamped section gets reduced to its first meaningful line.
        Returns count of files modified."""
        cutoff = date.today() - timedelta(days=older_than_days)
        modified = 0
        for log_file in DAILY_LOG_DIR.glob("*.md"):
            try:
                file_date = datetime.strptime(log_file.stem, "%Y-%m-%d").date()
                if file_date >= cutoff:
                    continue
                with open(log_file, "r", encoding="utf-8") as f:
                    content = f.read()
                # If it has multiple ### entries, compress to one-line summaries
                if content.count("### ") > 2:
                    lines = []
                    for line in content.split("\n"):
                        line = line.strip()
                        if line.startswith("### ["):
                            # Extract just the timestamp
                            lines.append(line)
                        elif line and not line.startswith("#") and not line.startswith("---"):
                            # Keep first meaningful line of each entry
                            if lines and lines[-1].startswith("### ["):
                                # This is the first line after a timestamp — keep it
                                summary = line[:120] + ("..." if len(line) > 120 else "")
                                lines.append(summary)
                                lines.append("")  # separator
                    # Reconstruct with header
                    header = f"# Daily Log — {log_file.stem}\n"
                    collapsed = header + "\n".join(lines) + "\n"
                    if len(collapsed) < len(content):
                        with open(log_file, "w", encoding="utf-8") as f:
                            f.write(collapsed)
                        modified += 1
            except (ValueError, OSError):
                continue
        return modified
