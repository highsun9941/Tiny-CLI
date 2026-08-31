from pathlib import Path

from tiny_cli.tools import read_file, replace_in_file, write_file


def test_file_tools(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert write_file("a.txt", "hello") == "wrote a.txt (5 chars)"
    assert read_file("a.txt") == "hello"
    assert replace_in_file("a.txt", "hello", "world") == "replaced 1 occurrence in a.txt"
    assert read_file("a.txt") == "world"
