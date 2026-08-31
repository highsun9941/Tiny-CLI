#!/usr/bin/env python3
"""Tiny-CLI: a deliberately small, model-driven coding agent.

The runtime intentionally contains no planner, subagents, policy engine,
permission heuristics, memory system, or retry orchestration. The model
chooses tools; Tiny-CLI executes them and returns the result.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI


SYSTEM_PROMPT = """You are a coding agent working directly in the current repository.
Decide what to do and use the available tools. The runtime is intentionally
minimal: there is no planner, permission layer, or automatic recovery logic.
Inspect files before changing them when useful, make the requested changes,
and run commands/tests when appropriate.
"""


TOOLS = [
    {
        "type": "function",
        "name": "read_file",
        "description": "Read a UTF-8 text file from the current working directory.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Write a UTF-8 text file, creating parent directories when needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "replace_in_file",
        "description": "Replace an exact text occurrence in a UTF-8 file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "run_command",
        "description": "Run a shell command in the current working directory and return stdout/stderr.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def _path(path: str) -> Path:
    """Resolve a user/model supplied path relative to the current directory."""
    return (Path.cwd() / path).resolve()


def read_file(path: str) -> str:
    return _path(path).read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    target = _path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"wrote {path} ({len(content)} chars)"


def replace_in_file(path: str, old: str, new: str) -> str:
    target = _path(path)
    content = target.read_text(encoding="utf-8")
    count = content.count(old)
    if count == 0:
        raise ValueError("old text was not found")
    if count > 1:
        raise ValueError(f"old text matched {count} times; make it unique")
    target.write_text(content.replace(old, new, 1), encoding="utf-8")
    return f"replaced 1 occurrence in {path}"


def run_command(command: str) -> str:
    result = subprocess.run(
        command,
        shell=True,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    output = (result.stdout + result.stderr).strip()
    return f"exit_code={result.returncode}\n{output}" if output else f"exit_code={result.returncode}"


def execute_tool(name: str, args: dict[str, Any]) -> str:
    if name == "read_file":
        return read_file(**args)
    if name == "write_file":
        return write_file(**args)
    if name == "replace_in_file":
        return replace_in_file(**args)
    if name == "run_command":
        return run_command(**args)
    raise ValueError(f"unknown tool: {name}")


def print_response(text: str) -> None:
    if text:
        print(text)
        print()


def main() -> int:
    model = os.getenv("TINY_CLI_MODEL")
    if not model:
        print("TINY_CLI_MODEL is required", file=sys.stderr)
        return 2

    client = OpenAI(
        api_key=os.getenv("TINY_CLI_API_KEY") or os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("TINY_CLI_BASE_URL") or None,
    )

    print(f"tiny-cli · model={model}")
    print("Type a task. Ctrl-D to exit.\n")

    history: list[dict[str, Any]] = [{"role": "developer", "content": SYSTEM_PROMPT}]

    while True:
        try:
            prompt = input("> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("^C")
            continue

        if not prompt.strip():
            continue

        history.append({"role": "user", "content": prompt})

        while True:
            response = client.responses.create(
                model=model,
                input=history,
                tools=TOOLS,
            )

            for item in response.output:
                if item.type == "message":
                    for part in item.content:
                        if getattr(part, "type", None) == "output_text":
                            print_response(part.text)

            calls = [item for item in response.output if item.type == "function_call"]
            history.extend(item.model_dump() for item in response.output)

            if not calls:
                break

            for call in calls:
                try:
                    args = json.loads(call.arguments)
                    result = execute_tool(call.name, args)
                except Exception as exc:  # deliberate: return raw tool failure to model
                    result = f"ERROR: {type(exc).__name__}: {exc}"
                history.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": result,
                    }
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
