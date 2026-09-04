from typing import Dict, Any, List, Optional
from ruby.memory_manager import MemoryManager

memory_mgr = MemoryManager()

def remember_person(name: str, relationship: str = "", notes: str = "") -> str:
    """Save or update information about a person in kaushik's life."""
    success = memory_mgr.add_known_person(name, relationship, notes)
    if success:
        return f"Successfully saved details for {name} to memory."
    return f"Failed to save details for {name}."


def update_user_preference(preference_key: str, preference_value: str) -> str:
    """Update a user preference or profile setting."""
    profile = memory_mgr.load_profile()
    prefs = profile.get("user", {}).get("preferences", {})
    prefs[preference_key] = preference_value
    success = memory_mgr.update_profile("user", "preferences", prefs)
    if success:
        return f"Saved preference '{preference_key}': '{preference_value}'."
    return f"Failed to update preference."


def record_routine(routine_description: str) -> str:
    """Record a user routine or habit."""
    success = memory_mgr.add_routine(routine_description)
    if success:
        return f"Recorded routine: {routine_description}"
    return "Failed to record routine."


def save_project_update(project_name: str, update_note: str) -> str:
    """Add a note or milestone to an active project file."""
    path = memory_mgr.append_project_note(project_name, update_note)
    return f"Logged update to project '{project_name}' ({path.name})."


def log_daily_event(summary: str, tags: Optional[List[str]] = None) -> str:
    """Log an important event, check-in, or context item to today's daily log."""
    path = memory_mgr.save_daily_log(summary, tags=tags)
    return f"Recorded entry in daily log ({path.name})."


# Anthropic Claude Tool Definitions
REMEMBER_PERSON_TOOL = {
    "name": "remember_person",
    "description": "Store or update information about a person in kaushik's life (friends, colleagues, family, contacts).",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Person's name or nickname."},
            "relationship": {"type": "string", "description": "Relationship to kaushik (e.g. 'friend', 'hackathon partner', 'colleague')."},
            "notes": {"type": "string", "description": "Important details or notes about them."}
        },
        "required": ["name"]
    }
}

UPDATE_PREFERENCE_TOOL = {
    "name": "update_user_preference",
    "description": "Update a preference or setting for kaushik.",
    "input_schema": {
        "type": "object",
        "properties": {
            "preference_key": {"type": "string", "description": "Name of the preference key."},
            "preference_value": {"type": "string", "description": "Value to set."}
        },
        "required": ["preference_key", "preference_value"]
    }
}

RECORD_ROUTINE_TOOL = {
    "name": "record_routine",
    "description": "Record a routine, habit, or recurring activity for kaushik (e.g. 'Morning chai at 9 AM', 'Gym every evening').",
    "input_schema": {
        "type": "object",
        "properties": {
            "routine_description": {"type": "string", "description": "Description of the routine or habit to record."}
        },
        "required": ["routine_description"]
    }
}

SAVE_PROJECT_UPDATE_TOOL = {
    "name": "save_project_update",
    "description": "Log an update, milestone, or technical note to an ongoing project or hackathon document in memory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "Name of the project (e.g. 'ruby', 'hackathon2026')."},
            "update_note": {"type": "string", "description": "The milestone, task, or note to record."}
        },
        "required": ["project_name", "update_note"]
    }
}

LOG_DAILY_EVENT_TOOL = {
    "name": "log_daily_event",
    "description": "Record an important milestone, user check-in, mood/stress follow-up, or key conversation summary to today's daily log.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Summary of the event or check-in to log."},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags (e.g. ['check-in', 'deadline', 'bugfix'])."
            }
        },
        "required": ["summary"]
    }
}
