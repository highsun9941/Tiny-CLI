import sys

from tiny_cli.app import main


def test_main_starts_ui_without_provider(monkeypatch) -> None:
    started = []

    def no_provider(*_args):
        raise RuntimeError("No provider configured. Add config")

    monkeypatch.setattr("tiny_cli.app.resolve_provider", no_provider)
    monkeypatch.setattr("tiny_cli.app.run", lambda provider: started.append(provider))
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
        lambda name, model: captured.update(name=name, model=model) or Provider(),
    )
    monkeypatch.setattr("tiny_cli.app.run", lambda provider: captured.update(provider=provider))
    monkeypatch.setattr(sys, "argv", ["tiny", "--provider", "custom", "--model", "model-2"])

    assert main() == 0
    assert captured["name"] == "custom"
    assert captured["model"] == "model-2"
    assert isinstance(captured["provider"], Provider)
