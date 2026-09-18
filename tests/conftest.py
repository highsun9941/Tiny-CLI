import pytest


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Tests must never use the developer's credentials or personal config."""
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "TINY_CLI_API_KEY",
                 "TINY_CLI_PROVIDER", "TINY_CLI_MODEL", "TINY_CLI_CONFIG", "OPENAI_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("tiny_cli.providers.DEFAULT_CONFIG", tmp_path / "missing.toml")
