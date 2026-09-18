from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from .providers import ProviderConfig
from .plugins import load_plugins
from .tools import TOOL_DEFINITIONS, execute_tool
from .transport import complete


@dataclass
class AgentEvent:
    kind: str
    text: str = ""
    tool: str = ""


class Agent:
    def __init__(
        self,
        provider: ProviderConfig,
        on_event: Callable[[AgentEvent], None] | None = None,
        *,
        plugins: list[str] | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.provider = provider
        self.on_event = on_event or (lambda _event: None)
        self.messages: list[dict[str, Any]] = []
        self.tools = deepcopy(TOOL_DEFINITIONS)
        self.tool_handlers: dict[str, Callable[..., str]] = {}
        self.before_request: list[Callable[[Agent], None]] = []
        self.event_handlers: list[Callable[[AgentEvent], None]] = []
        self.plugins = list(dict.fromkeys(plugins or []))
        self.client = client or httpx.Client(timeout=180.0)
        self._owns_client = client is None
        try:
            load_plugins(self, self.plugins)
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def add_tool(self, definition: dict[str, Any], handler: Callable[..., str]) -> None:
        name = definition["function"]["name"]
        if any(tool["function"]["name"] == name for tool in self.tools):
            raise ValueError(f"Tool already registered: {name}")
        self.tools.append(deepcopy(definition))
        self.tool_handlers[name] = handler

    def _emit(self, event: AgentEvent) -> None:
        self.on_event(event)
        for handler in self.event_handlers:
            handler(event)

    def ask(self, prompt: str) -> None:
        self.messages.append({"role": "user", "content": prompt})
        while True:
            for hook in self.before_request:
                hook(self)
            message = complete(self.client, self.provider, self.messages, self.tools)
            self.messages.append(message)

            content = message.get("content")
            if content:
                self._emit(AgentEvent(kind="assistant", text=content))

            calls = message.get("tool_calls") or []
            if not calls:
                self._emit(AgentEvent(kind="turn_end"))
                return

            for call in calls:
                name = call["function"]["name"]
                arguments = call["function"].get("arguments", "{}")
                self._emit(AgentEvent(kind="tool_start", tool=name))
                failed = False
                try:
                    args = json.loads(arguments)
                    if not isinstance(args, dict):
                        raise ValueError("Tool arguments must be a JSON object")
                    handler = self.tool_handlers.get(name)
                    result = handler(**args) if handler else execute_tool(name, args)
                    if not isinstance(result, str):
                        raise TypeError("Tool results must be strings")
                except Exception as exc:
                    failed = True
                    result = f"ERROR: {type(exc).__name__}: {exc}"
                self.messages.append({"role": "tool", "tool_call_id": call["id"], "content": result, "_is_error": failed})
                self._emit(AgentEvent(kind="tool_end", tool=name, text=result))
