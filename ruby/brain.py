import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from ruby.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    BASE_SYSTEM_PROMPT,
    LLM_PROVIDERS,
    OPENROUTER_BASE_URL,
)
from ruby.memory_manager import MemoryManager
from ruby.tools.web_search import (
    search_web,
    fetch_webpage,
    WEB_SEARCH_TOOL_DEFINITION,
    FETCH_WEBPAGE_TOOL_DEFINITION,
)
from ruby.tools.memory_tools import (
    remember_person,
    update_user_preference,
    record_routine,
    save_project_update,
    log_daily_event,
    REMEMBER_PERSON_TOOL,
    UPDATE_PREFERENCE_TOOL,
    RECORD_ROUTINE_TOOL,
    SAVE_PROJECT_UPDATE_TOOL,
    LOG_DAILY_EVENT_TOOL,
)
from ruby.tools.browser_tools import (
    send_whatsapp_message,
    browse_url,
    capture_page_screenshot,
    SEND_WHATSAPP_MESSAGE_TOOL,
    BROWSE_URL_TOOL,
    CAPTURE_SCREENSHOT_TOOL,
)
from ruby.tools.os_tools import (
    launch_app,
    read_memory_file,
    write_memory_file,
    delete_memory_file,
    execute_script,
    LAUNCH_APP_TOOL,
    READ_MEMORY_FILE_TOOL,
    WRITE_MEMORY_FILE_TOOL,
    DELETE_MEMORY_FILE_TOOL,
    EXECUTE_SCRIPT_TOOL,
)

try:
    from openai import OpenAI
    from openai import (
        APIConnectionError,
        RateLimitError,
        APIStatusError,
        OpenAIError,
    )
except ImportError:
    OpenAI = None
    APIConnectionError = RateLimitError = APIStatusError = OpenAIError = Exception


def _to_openai_tools(defs: list) -> list:
    """Convert Anthropic-format tool definitions to OpenAI/OpenRouter format.

    Anthropic uses {"name", "description", "input_schema"}; OpenAI uses
    {"type": "function", "function": {"name", "description", "parameters"}}.
    """
    converted = []
    for d in defs:
        converted.append({
            "type": "function",
            "function": {
                "name": d.get("name", ""),
                "description": d.get("description", ""),
                "parameters": d.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return converted


class RubyBrain:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)
        self.model = model or os.getenv("ANTHROPIC_MODEL", ANTHROPIC_MODEL)
        self.memory_mgr = MemoryManager()
        self.messages: List[Dict[str, Any]] = []

        # Run lightweight housekeeping once per session: compress old logs,
        # prune very old ones. Silent — never blocks the user.
        try:
            self.memory_mgr.summarize_old_entries(older_than_days=7)
            self.memory_mgr.cleanup_old_logs(keep_days=30)
        except Exception:
            pass
        
        # Available tools and implementations
        self.tool_definitions = [
            WEB_SEARCH_TOOL_DEFINITION,
            FETCH_WEBPAGE_TOOL_DEFINITION,
            REMEMBER_PERSON_TOOL,
            UPDATE_PREFERENCE_TOOL,
            RECORD_ROUTINE_TOOL,
            SAVE_PROJECT_UPDATE_TOOL,
            LOG_DAILY_EVENT_TOOL,
            SEND_WHATSAPP_MESSAGE_TOOL,
            BROWSE_URL_TOOL,
            CAPTURE_SCREENSHOT_TOOL,
            LAUNCH_APP_TOOL,
            READ_MEMORY_FILE_TOOL,
            WRITE_MEMORY_FILE_TOOL,
            DELETE_MEMORY_FILE_TOOL,
            EXECUTE_SCRIPT_TOOL,
        ]
        
        self.tool_dispatch: Dict[str, Callable] = {
            "web_search": self._wrap_tool(search_web),
            "fetch_webpage": self._wrap_tool(fetch_webpage),
            "remember_person": self._wrap_tool(remember_person),
            "update_user_preference": self._wrap_tool(update_user_preference),
            "record_routine": self._wrap_tool(record_routine),
            "save_project_update": self._wrap_tool(save_project_update),
            "log_daily_event": self._wrap_tool(log_daily_event),
            "send_whatsapp_message": self._wrap_tool(send_whatsapp_message),
            "browse_url": self._wrap_tool(browse_url),
            "capture_page_screenshot": self._wrap_tool(capture_page_screenshot),
            "launch_app": self._wrap_tool(launch_app),
            "read_memory_file": self._wrap_tool(read_memory_file),
            "write_memory_file": self._wrap_tool(write_memory_file),
            "delete_memory_file": self._wrap_tool(delete_memory_file),
            "execute_script": self._wrap_tool(execute_script),
        }

        # --- Multi-provider LLM failover -------------------------------------
        # Callers passing an explicit api_key/model (old interface) get a single
        # "Override" provider; otherwise Ruby uses the ordered provider list from
        # config.py and falls through to the next provider when one fails.
        if api_key is not None or model is not None:
            self.providers = [{
                "name": "Override",
                "api_key": self.api_key,
                "base_url": OPENROUTER_BASE_URL,
                "model": self.model,
            }]
        else:
            self.providers = [dict(p) for p in LLM_PROVIDERS]
        self._active_provider = None  # last known-working provider (same session)
        self._clients = {}            # provider name -> OpenAI client (lazy)

        # Backward-compat client on the first provider; chat() uses per-provider
        # clients via _client_for(), this is only for any external reader.
        self.client = None
        if OpenAI and self.providers:
            try:
                self.client = self._client_for(self.providers[0])
            except Exception as e:
                print(f"[RubyBrain] Warning: Could not initialize OpenAI client: {e}")

    def _client_for(self, provider: dict):
        """Lazily build (and cache) the OpenAI client for one provider."""
        name = provider["name"]
        if name not in self._clients:
            self._clients[name] = OpenAI(
                api_key=provider["api_key"],
                base_url=provider["base_url"],
            )
        return self._clients[name]

    def _api_error_message(self, e: Exception) -> str:
        """Friendly, user-facing message for a provider/API failure."""
        if isinstance(e, APIConnectionError):
            return f"I had trouble connecting to the network to think through that: {e}. Want me to try again?"
        if isinstance(e, RateLimitError):
            return f"Hit the API rate limit for a second: {e}. Let's pause a moment and retry."
        if isinstance(e, APIStatusError):
            return f"API returned an error ({e.status_code}): {e}"
        if isinstance(e, OpenAIError):
            return f"API error: {e}"
        return f"Something broke on my end while processing that: {e}"

    def _wrap_tool(self, func: Callable) -> Callable:
        import inspect
        sig = inspect.signature(func)
        allowed = set(sig.parameters.keys())

        def wrapper(**kwargs):
            # Only forward parameters the function actually accepts.
            # This prevents Claude-hallucinated extra keys from crashing the call
            # and ensures internal-only params (e.g. pre_approved) can never be
            # injected through the tool interface.
            filtered = {k: v for k, v in kwargs.items() if k in allowed}
            try:
                return func(**filtered)
            except Exception as e:
                return f"Tool execution failed: {str(e)}"
        return wrapper

    def assemble_system_prompt(self, voice_mode: bool = False) -> str:
        current_time_str = datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")
        time_context = f"\nCURRENT LOCAL TIME: {current_time_str}\n"
        memory_context = self.memory_mgr.build_memory_context()

        # List available tools so the model doesn't hallucinate non-existent ones
        tool_names = [d["name"] for d in self.tool_definitions]
        tools_context = f"\nAVAILABLE TOOLS (use ONLY these exact names): {', '.join(tool_names)}\n"

        base = f"{BASE_SYSTEM_PROMPT}\n{time_context}\n{memory_context}{tools_context}"
        if voice_mode:
            base += "\n[VOICE MODE ACTIVE — Keep every response to 1-3 short sentences. One clear answer, no paragraphs.]"
        return base

    def reset_conversation(self):
        """Clears short-term conversation context for a new session."""
        self.messages = []

    def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        handler = self.tool_dispatch.get(tool_name)
        if not handler:
            return f"Error: Tool '{tool_name}' not found."
        try:
            return str(handler(**tool_args))
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

    def chat(self, user_input: str, on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None, voice_mode: bool = False) -> str:
        """
        Processes a user message, runs the reasoning loop with the model API
        (OpenRouter/OpenAI-compatible) and tools, and returns Ruby's response.

        When voice_mode=True, a short instruction is appended to the system prompt
        so the model keeps spoken responses brief and conversational.
        """
        if not self.providers:
            # Helpful guidance if no API provider is configured yet
            return (
                "Hey! I need an API key to start thinking. "
                "Please add `ANTHROPIC_API_KEY=your_key_here` to your `.env` file in `C:\\Users\\sudha\\OneDrive\\ruby` "
                "or set it in your environment variables, and I'll be ready to roll!"
            )
        if OpenAI is None:
            return "I need the `openai` package to think. How about a quick: pip install openai"

        # Append user message
        self.messages.append({"role": "user", "content": user_input})

        system_prompt = self.assemble_system_prompt(voice_mode=voice_mode)
        max_iterations = 10  # Safety limit for multi-step tool calls
        history_base = len(self.messages)  # index right after the user message

        # Provider order: the last known-working provider first (so a healthy
        # session doesn't re-hit a dead provider on every message), then the rest
        # in config priority order.
        order = [dict(p) for p in self.providers]
        if self._active_provider:
            active = next((p for p in order if p["name"] == self._active_provider), None)
            if active:
                order = [active] + [p for p in order if p["name"] != self._active_provider]

        failures = []  # provider names that were tried and failed this turn
        for provider in order:
            try:
                client = self._client_for(provider)

                for _ in range(max_iterations):
                    request = {
                        "model": provider["model"],
                        "max_tokens": 4096,
                        "messages": [{"role": "system", "content": system_prompt}] + self.messages,
                    }
                    if self.tool_definitions:
                        request["tools"] = _to_openai_tools(self.tool_definitions)

                    try:
                        response = client.chat.completions.create(**request)
                    except APIStatusError as e:
                        if e.status_code == 400 and "tool" in str(e).lower():
                            # Model hallucinated an invalid tool — retry without tools
                            request.pop("tools", None)
                            response = client.chat.completions.create(**request)
                        else:
                            raise
                    message = response.choices[0].message

                    # Check for tool calls (OpenAI/OpenRouter format)
                    tool_calls = getattr(message, "tool_calls", None)
                    if tool_calls:
                        # Keep the assistant message (with tool_calls) in history.
                        assistant_entry = {"role": "assistant", "content": message.content, "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                            }
                            for tc in tool_calls
                        ]}
                        self.messages.append(assistant_entry)

                        tool_results = []
                        for tc in tool_calls:
                            tool_name = tc.function.name
                            import json as _json
                            try:
                                tool_input = _json.loads(tc.function.arguments or "{}")
                            except Exception:
                                tool_input = {}
                            tool_id = tc.id

                            if on_tool_call:
                                on_tool_call(tool_name, tool_input)

                            result = self.execute_tool(tool_name, tool_input)
                            tool_results.append({
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "content": str(result)
                            })

                        self.messages.extend(tool_results)
                        # Continue loop to let the model process tool outputs
                        continue
                    else:
                        # Final assistant message reached
                        final_text = message.content or ""
                        self.messages.append({"role": "assistant", "content": final_text})
                        self._active_provider = provider["name"]
                        return final_text

                # Exhausted the iteration budget: model nudged into a tool loop.
                # That's not a provider outage, so don't fail over to another key.
                return "I got caught in a tool loop while executing that action. Could you try again or rephrase?"

            except (APIConnectionError, RateLimitError, APIStatusError, OpenAIError) as e:
                # Only fail over if no side-effecting tool has run this turn.
                # If one already ran (e.g. a WhatsApp message or file write), a
                # retry against another provider could re-execute it — instead
                # surface the error and let the user decide.
                if len(self.messages) != history_base:
                    return self._api_error_message(e)
                failures.append(provider["name"])
                print(f"[RubyBrain] Provider {provider['name']} failed "
                      f"({e.__class__.__name__}) → trying next")
                # Reset history to just after the user message, so the next
                # provider starts clean without the user message being added twice.
                del self.messages[history_base:]
            except Exception as e:
                return self._api_error_message(e)

        tried = ", ".join(failures) or "no providers configured"
        return (
            f"I tried all {len(order)} sources ({tried}) and every one failed. "
            "Everything was tested — I'll reconnect when a source is back. "
            "Ask me again in a bit."
        )
