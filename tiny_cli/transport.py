"""Wire-format adapters only: no prompts, routing, retries, or context policy."""
from __future__ import annotations

import json
from typing import Any

import httpx

from .providers import ProviderConfig


def _anthropic_history(messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    history: list[dict[str, Any]] = []
    system: list[dict[str, Any]] = []
    for message in messages:
        role = message["role"]
        content = message.get("content")
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) and content else content or []
        if role in {"system", "developer"}:
            system.extend(blocks)
            continue
        if role == "tool":
            role = "user"
            blocks = [{"type": "tool_result", "tool_use_id": message["tool_call_id"],
                       "content": content, "is_error": message.get("_is_error", False)}]
        elif role == "assistant":
            if "_anthropic_content" in message:
                # Retain native blocks, including thinking signatures, verbatim.
                blocks = message["_anthropic_content"]
            else:
                blocks = list(blocks)
                for call in message.get("tool_calls") or []:
                    blocks.append({"type": "tool_use", "id": call["id"],
                                   "name": call["function"]["name"],
                                   "input": json.loads(call["function"]["arguments"])})
        if history and history[-1]["role"] == role:
            history[-1]["content"].extend(blocks)
        else:
            history.append({"role": role, "content": list(blocks)})
    return history, system


def complete(
    client: httpx.Client,
    provider: ProviderConfig,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    key = provider.api_key()
    headers = {"Content-Type": "application/json"}
    if provider.api_format == "anthropic":
        history, system = _anthropic_history(messages)
        headers["anthropic-version"] = "2023-06-01"
        if key:
            headers["x-api-key"] = key
        body = {
            "model": provider.model,
            "max_tokens": provider.max_tokens,
            "messages": history,
            "tools": [{"name": t["function"]["name"],
                       "description": t["function"]["description"],
                       "input_schema": t["function"]["parameters"]} for t in tools],
        }
        if system:
            body["system"] = system
        endpoint = "messages"
    else:
        if key:
            headers["Authorization"] = f"Bearer {key}"
        body = {
            "model": provider.model,
            "messages": [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages],
            "tools": tools,
            "tool_choice": "auto",
        }
        endpoint = "chat/completions"
    response = client.post(f"{provider.base_url.rstrip('/')}/{endpoint}", headers=headers, json=body)
    response.raise_for_status()
    payload = response.json()
    if provider.api_format == "openai":
        return payload["choices"][0]["message"]
    blocks = payload["content"]
    return {
        "role": "assistant",
        "content": "\n".join(block["text"] for block in blocks if block["type"] == "text"),
        "tool_calls": [{"id": block["id"], "type": "function", "function": {
            "name": block["name"], "arguments": json.dumps(block["input"]),
        }} for block in blocks if block["type"] == "tool_use"],
        "_anthropic_content": blocks,
    }
