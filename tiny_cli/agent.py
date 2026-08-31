from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import httpx

from .providers import ProviderConfig
from .tools import TOOL_DEFINITIONS, execute_tool

SYSTEM_PROMPT = """You are a coding agent working directly in the current repository.
Decide what to do and use the available tools. The runtime is intentionally
minimal: there is no planner, permission layer, subagent system, memory,
or automatic recovery logic. The model owns planning, sequencing, diagnosis,
and retries. Inspect files when useful, make requested changes, and run
commands/tests when appropriate."""


@dataclass
class AgentEvent:
    kind: str
    text: str = ""
    tool: str = ""


class Agent:
    def __init__(self, provider: ProviderConfig, on_event: Callable[[AgentEvent], None] | None = None) -> None:
        self.provider = provider
        self.on_event = on_event or (lambda _event: None)
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.client = httpx.Client(timeout=180.0)

    def _emit(self, event: AgentEvent) -> None:
        self.on_event(event)

    def ask(self, prompt: str) -> None:
        self.messages.append({"role": "user", "content": prompt})
        while True:
            response = self.client.post(
                f"{self.provider.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.provider.api_key()}", "Content-Type": "application/json"},
                json={"model": self.provider.model, "messages": self.messages, "tools": TOOL_DEFINITIONS, "tool_choice": "auto"},
            )
            response.raise_for_status()
            payload = response.json()
            message = payload["choices"][0]["message"]
            self.messages.append(message)

            content = message.get("content")
            if content:
                self._emit(AgentEvent(kind="assistant", text=content))

            calls = message.get("tool_calls") or []
            if not calls:
                return

            for call in calls:
                name = call["function"]["name"]
                arguments = call["function"].get("arguments", "{}")
                import json
                args = json.loads(arguments)
                self._emit(AgentEvent(kind="tool_start", tool=name))
                try:
                    result = execute_tool(name, args)
                except Exception as exc:
                    result = f"ERROR: {type(exc).__name__}: {exc}"
                self.messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
                self._emit(AgentEvent(kind="tool_end", tool=name, text=result))
