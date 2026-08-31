from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _path(path: str) -> Path:
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
    result = subprocess.run(command, shell=True, cwd=Path.cwd(), text=True, capture_output=True)
    output = (result.stdout + result.stderr).strip()
    return f"exit_code={result.returncode}\n{output}" if output else f"exit_code={result.returncode}"


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function", "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file from the current working directory.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False},
        },
    },
    {
        "type": "function", "function": {
            "name": "write_file",
            "description": "Write a UTF-8 text file, creating parent directories when needed.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False},
        },
    },
    {
        "type": "function", "function": {
            "name": "replace_in_file",
            "description": "Replace one exact text occurrence in a UTF-8 file.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, "required": ["path", "old", "new"], "additionalProperties": False},
        },
    },
    {
        "type": "function", "function": {
            "name": "run_command",
            "description": "Run a shell command in the current working directory and return stdout/stderr.",
            "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"], "additionalProperties": False},
        },
    },
]


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
