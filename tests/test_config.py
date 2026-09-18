import sys

import pytest

from tiny_cli.app import main
from tiny_cli.providers import NoProviderError


def test_main_starts_ui_without_provider(monkeypatch) -> None:
    started = []

    def no_provider(*_args):
        raise NoProviderError("No provider configured. Add config")

    monkeypatch.setattr("tiny_cli.app.resolve_provider", no_provider)
    monkeypatch.setattr("tiny_cli.app.load_config", lambda *_args: {})
    monkeypatch.setattr("tiny_cli.app.run", lambda provider, **_kwargs: started.append(provider))
    monkeypatch.setattr(sys, "argv", ["tiny"])

    assert main() == 0
    assert started == [None]


def test_main_passes_provider_and_model_override(monkeypatch) -> None:
    captured = {}

    class Provider:
        name = "Test"
        model = "model-2"

    monkeypatch.setattr(
        "tiny_cli.app.resolve_provider",
        lambda name, model, path: captured.update(name=name, model=model) or Provider(),
    )
    monkeypatch.setattr("tiny_cli.app.load_config", lambda *_args: {})
    monkeypatch.setattr("tiny_cli.app.run", lambda provider, **_kwargs: captured.update(provider=provider))
    monkeypatch.setattr(sys, "argv", ["tiny", "--provider", "custom", "--model", "model-2"])

    assert main() == 0
    assert captured["name"] == "custom"
    assert captured["model"] == "model-2"
    assert isinstance(captured["provider"], Provider)


@pytest.mark.parametrize("disabled", [False, True])
def test_explicit_config_and_plugin_selection(tmp_path, monkeypatch, disabled):
    config = tmp_path / "config.toml"
    config.write_text('''[plugins]
enabled = ["configured_plugin:setup"]
[providers.local]
base_url = "http://localhost:1234/v1"
api_key_env = ""
model = "local"
''')
    captured = {}
    monkeypatch.setattr("tiny_cli.app.run", lambda provider, **kwargs: captured.update(provider=provider, **kwargs))
    args = ["tiny", "--config", str(config), "--plugin", "explicit_plugin:setup"]
    monkeypatch.setattr(sys, "argv", args + (["--no-plugins"] if disabled else []))
    assert main() == 0
    assert captured["config_path"] == config
    assert captured["provider"].model == "local"
    assert captured["plugins"] == ([] if disabled else ["configured_plugin:setup", "explicit_plugin:setup"])
