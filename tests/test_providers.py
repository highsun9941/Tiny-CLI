from pathlib import Path

from tiny_cli.providers import load_providers, resolve_provider


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
