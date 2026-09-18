from pathlib import Path

import pytest

from tiny_cli.providers import ProviderConfig, load_config, load_providers, resolve_provider


def test_load_custom_provider(tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text(
        """
[providers.deepseek]
name = "DeepSeek"
base_url = "https://api.deepseek.com/v1"
api_key_env = "DEEPSEEK_API_KEY"
model = "deepseek-chat"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    providers = load_providers(config)
    assert providers["deepseek"].base_url == "https://api.deepseek.com/v1"
    assert providers["deepseek"].model == "deepseek-chat"


def test_resolve_provider_from_config(tmp_path: Path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text(
        """
[providers.custom]
name = "Custom"
base_url = "https://example.com/v1"
api_key_env = "CUSTOM_API_KEY"
model = "custom-model"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("tiny_cli.providers.DEFAULT_CONFIG", config)
    provider = resolve_provider("custom")
    assert provider.name == "Custom"
    assert provider.model == "custom-model"


def test_profile_selection_and_model_override_precedence(tmp_path, monkeypatch):
    config = tmp_path / "profiles.toml"
    config.write_text('''default_provider = "z"
[providers.a]
base_url = "http://localhost:1234/v1"
api_key_env = ""
model = "local-model"
[providers.z]
base_url = "https://claude.test/v1"
api_key_env = "CLAUDE_KEY"
model = "configured-model"
api_format = "anthropic"
max_tokens = 8192
''')
    monkeypatch.setenv("TINY_CLI_CONFIG", str(config))
    assert resolve_provider().model == "configured-model"
    monkeypatch.setenv("TINY_CLI_MODEL", "env-model")
    assert resolve_provider().model == "env-model"
    selected = resolve_provider(model="cli-model")
    assert selected.model == "cli-model"
    assert selected.api_format == "anthropic" and selected.max_tokens == 8192
    monkeypatch.setenv("TINY_CLI_PROVIDER", "a")
    assert resolve_provider().api_key() == ""
    assert resolve_provider("z").api_format == "anthropic"


def test_empty_compose_environment_uses_builtin_defaults(monkeypatch):
    monkeypatch.setenv("TINY_CLI_MODEL", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    assert resolve_provider().model == "gpt-5"
    assert resolve_provider().base_url == "https://api.openai.com/v1"


def test_explicit_missing_config_is_not_silently_ignored(tmp_path):
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(tmp_path / "typo.toml")


def test_keyless_provider_is_explicit(monkeypatch):
    provider = ProviderConfig("local", "http://localhost/v1", "NEEDED_KEY", "model")
    monkeypatch.delenv("NEEDED_KEY", raising=False)
    with pytest.raises(RuntimeError, match="NEEDED_KEY"):
        provider.api_key()


def test_unknown_api_format_fails_at_configuration_time():
    with pytest.raises(ValueError, match="API format"):
        ProviderConfig("test", "https://test/v1", "", "model", "typo")
