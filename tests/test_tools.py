from pathlib import Path

import pytest

from tiny_cli.tools import execute_tool, run_command


def test_shell_can_write_and_read_files_in_working_directory(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = execute_tool("run_command", {"command": "printf 'hello\\n' > a.txt && cat a.txt"})
    assert result == "exit_code=0\nhello"
    assert (tmp_path / "a.txt").read_text() == "hello\n"


def test_shell_returns_exit_code_and_both_output_streams():
    result = run_command("printf 'output\\n'; printf 'error\\n' >&2; exit 7")
    assert result == "exit_code=7\noutput\nerror"


@pytest.mark.parametrize("name", ["read_file", "write_file", "replace_in_file"])
def test_removed_file_tools_are_not_executable(name):
    with pytest.raises(ValueError, match=f"unknown tool: {name}"):
        execute_tool(name, {})
