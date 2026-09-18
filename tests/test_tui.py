import asyncio
import threading

from textual.widgets import Input

from tiny_cli.providers import ProviderConfig
from tiny_cli.tui import TinyApp


class FakeAgent:
    instances = []

    def __init__(self, provider, on_event, *, plugins):
        self.provider = provider
        self.plugins = plugins
        self.closed = False
        self.messages = []
        self.instances.append(self)

    def close(self):
        self.closed = True


def test_switch_uses_selected_config_and_preserves_plugin_selection(tmp_path, monkeypatch):
    config = tmp_path / "profiles.toml"
    config.write_text('''[providers.second]
name = "Second"
base_url = "http://localhost/v1"
api_key_env = ""
model = "second-model"
''')
    monkeypatch.setattr("tiny_cli.tui.Agent", FakeAgent)
    first = ProviderConfig("First", "http://localhost/v1", "", "first-model")

    async def scenario():
        app = TinyApp(first, config_path=config, plugins=["example:setup"])
        async with app.run_test() as pilot:
            old = app.agent
            app._command("/use second override")
            assert old.closed
            assert app.provider.model == "override"
            assert app.agent.plugins == ["example:setup"]
            active = app.agent
            app._command("/use missing")
            assert app.agent is active and not active.closed
            app.busy = True
            app._command("/use second")
            app._command("/clear")
            assert app.agent is active
            app.busy = False
            app._command("/clear")
            assert active.closed
            app._add("assistant", "[not-markup] literal [/broken]")
            await pilot.pause()
        assert app.agent.closed
    asyncio.run(scenario())


def test_busy_task_does_not_start_overlapping_requests(monkeypatch):
    started, release = threading.Event(), threading.Event()
    prompts = []

    class SlowAgent(FakeAgent):
        def ask(self, prompt):
            prompts.append(prompt)
            started.set()
            release.wait(timeout=5)

    monkeypatch.setattr("tiny_cli.tui.Agent", SlowAgent)
    provider = ProviderConfig("Test", "http://localhost/v1", "", "model")

    async def scenario():
        app = TinyApp(provider)
        async with app.run_test() as pilot:
            composer = app.query_one(Input)
            app.on_input_submitted(Input.Submitted(composer, "first"))
            assert app.busy
            try:
                await asyncio.to_thread(started.wait, 2)
                app.on_input_submitted(Input.Submitted(composer, "second"))
                assert prompts == ["first"]
            finally:
                release.set()
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert not app.busy
    asyncio.run(scenario())
