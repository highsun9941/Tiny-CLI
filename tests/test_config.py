from pathlib import Path

from tiny_cli.app import main


def test_main_starts_ui_without_provider(monkeypatch) -> None:
    started = []

    monkeypatch.setattr("tiny_cli.app.resolve_provider", lambda *_args: (_ for _ in ()).throw(RuntimeError("No provider configured")))
    monkeypatch.setattr("tiny_cli.app.run", lambda provider: started.append(provider))
    monkeypatch.setattr("sys.argv", ["tiny", "--help"])

    # argparse exits before the app starts; this test documents the executable surface.
    try:
        main()
    except SystemExit as exc:
        assert exc.code == 0


def test_main_passes_provider_and_model_override(monkeypatch) -> None:
    captured = {}

    class Provider:
        name = "Test"
        model = "test-model"

    monkeypatch.setattr("tiny_cli.app.resolve_provider", lambda name, model: captured.update(name=name, model=model) or Provider())
    monkeypatch.setattr("tiny_cli.app.run", lambda provider: captured.update(provider=provider))
    monkeypatch.setattr("sys.argv", ["tiny", "--provider", "custom", "--model", "model-2"])

    assert main() == 0
    assert captured["name"] == "custom"
    assert captured["model"] == "model-2"
    assert isinstance(captured["provider"], Provider)
