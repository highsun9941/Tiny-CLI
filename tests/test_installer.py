"""Exercise the piped installer with isolated command stubs; no network is needed."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "install.sh"


@pytest.fixture
def installer(tmp_path):
    commands = tmp_path / "commands"
    commands.mkdir()
    for name in ("bash", "sh", "uname", "mkdir", "mktemp", "rm", "cp", "cat"):
        (commands / name).symlink_to(shutil.which(name))
    uv = tmp_path / "uv-stub"
    uv.write_text(f"#!{sys.executable}\n" + '''
import json, os, pathlib, sys
with open(os.environ['TINY_TEST_UV_LOG'], 'a') as output:
    output.write(json.dumps({'args': sys.argv[1:],
        'tools': os.environ['UV_TOOL_DIR'],
        'python': os.environ['UV_PYTHON_INSTALL_DIR']}) + '\\n')
if os.environ.get('TINY_TEST_FAIL_UV'):
    sys.exit(41)
command = pathlib.Path(os.environ['UV_TOOL_BIN_DIR']) / 'tiny'
command.write_text('#!/bin/sh\\nexit 0\\n')
command.chmod(0o755)
''')
    uv.chmod(0o755)
    curl = commands / "curl"
    curl.write_text(f"#!{sys.executable}\n" + '''
import json, os, pathlib, sys
path = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])
pathlib.Path(os.environ['TINY_TEST_CURL_LOG']).write_text(json.dumps(sys.argv[1:]))
if os.environ.get('TINY_TEST_FAIL_DOWNLOAD'):
    path.write_text('touch "' + os.environ['TINY_TEST_BAD_DOWNLOAD_MARKER'] + '"\\n')
    sys.exit(22)
path.write_text('mkdir -p "$UV_UNMANAGED_INSTALL"\\ncp "$TINY_TEST_UV_STUB" "$UV_UNMANAGED_INSTALL/uv"\\n')
''')
    curl.chmod(0o755)
    env = os.environ.copy()
    env.update({
        "PATH": str(commands),
        "TINY_CLI_INSTALL_DIR": str(tmp_path / "runtime with spaces"),
        "TINY_CLI_BIN_DIR": str(tmp_path / "bin with spaces"),
        "TINY_TEST_UV_STUB": str(uv),
        "TINY_TEST_UV_LOG": str(tmp_path / "uv.jsonl"),
        "TINY_TEST_CURL_LOG": str(tmp_path / "curl.json"),
        "TINY_TEST_BAD_DOWNLOAD_MARKER": str(tmp_path / "bad-download-executed"),
    })
    env.pop("TINY_CLI_REF", None)

    def run(*args):
        return subprocess.run(
            [str(commands / "bash"), "-s", "--", *args],
            input=SCRIPT.read_text(), text=True, capture_output=True, env=env,
            cwd=tmp_path, timeout=10,
        )
    return run, env, commands


def test_piped_install_and_reinstall_use_repository_source(installer):
    run, env, commands = installer
    (commands / "uv").symlink_to(env["TINY_TEST_UV_STUB"])
    env["TINY_CLI_REF"] = "main"
    for _ in range(2):
        result = run("--ref", "test-commit")
        assert result.returncode == 0, result.stderr
        assert "Tiny-CLI is installed" in result.stdout
        assert "export PATH=" in result.stdout
    calls = [json.loads(line) for line in Path(env["TINY_TEST_UV_LOG"]).read_text().splitlines()]
    assert len(calls) == 2
    assert calls[0]["args"][-1] == "https://github.com/highsun9941/Tiny-CLI/archive/test-commit.tar.gz"
    assert calls[0]["tools"] == env["TINY_CLI_INSTALL_DIR"] + "/tools"
    assert calls[0]["python"] == env["TINY_CLI_INSTALL_DIR"] + "/python"
    assert "--managed-python" in calls[0]["args"]
    assert "--force" not in calls[0]["args"]
    assert not Path(env["TINY_TEST_CURL_LOG"]).exists()


def test_bootstraps_uv_without_python_or_git_on_path(installer):
    run, env, commands = installer
    assert not any((commands / name).exists() for name in ("uv", "python", "python3", "git"))
    result = run()
    assert result.returncode == 0, result.stderr
    assert (Path(env["TINY_CLI_INSTALL_DIR"]) / "uv/uv").exists()
    args = json.loads(Path(env["TINY_TEST_CURL_LOG"]).read_text())
    assert "https://astral.sh/uv/install.sh" in args
    assert not Path(args[args.index("-o") + 1]).parent.exists()
    # Subsequent runs reuse the private uv binary.
    (commands / "curl").unlink()
    (commands / "curl").write_text("#!/bin/sh\nexit 99\n")
    (commands / "curl").chmod(0o755)
    assert run().returncode == 0


def test_failed_download_is_never_executed(installer):
    run, env, _ = installer
    env["TINY_TEST_FAIL_DOWNLOAD"] = "1"
    result = run()
    assert result.returncode != 0
    assert "Could not download uv" in result.stderr
    assert "Tiny-CLI is installed" not in result.stdout
    assert not Path(env["TINY_TEST_BAD_DOWNLOAD_MARKER"]).exists()
    assert not Path(env["TINY_TEST_UV_LOG"]).exists()
    args = json.loads(Path(env["TINY_TEST_CURL_LOG"]).read_text())
    assert not Path(args[args.index("-o") + 1]).parent.exists()


def test_failed_install_preserves_existing_command(installer):
    run, env, commands = installer
    (commands / "uv").symlink_to(env["TINY_TEST_UV_STUB"])
    env["TINY_TEST_FAIL_UV"] = "1"
    existing = Path(env["TINY_CLI_BIN_DIR"]) / "tiny"
    existing.parent.mkdir()
    existing.write_text("existing application")
    result = run()
    assert result.returncode != 0
    assert "Tiny-CLI is installed" not in result.stdout
    assert existing.read_text() == "existing application"


@pytest.mark.parametrize("args", [("--ref",), ("--ref", "../other"), ("--unknown",)])
def test_bad_arguments_fail_before_installing(installer, args):
    run, env, _ = installer
    assert run(*args).returncode != 0
    assert not Path(env["TINY_TEST_UV_LOG"]).exists()
    assert not Path(env["TINY_TEST_CURL_LOG"]).exists()


def test_help_needs_no_network_or_runtime(installer):
    run, env, commands = installer
    (commands / "curl").unlink()
    assert run("--help").returncode == 0
    assert not Path(env["TINY_CLI_INSTALL_DIR"]).exists()
