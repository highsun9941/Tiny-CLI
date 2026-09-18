from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def run_command(command: str) -> str:
    result = subprocess.run(command, shell=True, cwd=Path.cwd(), text=True, capture_output=True)
    output = (result.stdout + result.stderr).strip()
    return f"exit_code={result.returncode}\n{output}" if output else f"exit_code={result.returncode}"


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function", "function": {
            "name": "run_command",
            "description": "Run a shell command in the current working directory and return its exit code, stdout, and stderr.",
            "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"], "additionalProperties": False},
        },
    },
]


def execute_tool(name: str, args: dict[str, Any]) -> str:
    if name == "run_command":
        return run_command(**args)
    raise ValueError(f"unknown tool: {name}")
