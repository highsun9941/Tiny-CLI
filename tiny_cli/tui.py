from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from .agent import Agent, AgentEvent
from .providers import ProviderConfig, load_providers, resolve_provider

CSS = """
Screen { background: #0b0d10; color: #e6e8eb; }
Header { background: #11151a; color: #e6e8eb; }
#chat { height: 1fr; padding: 1 2; scrollbar-size: 1 1; }
#composer { height: auto; border: round #303842; padding: 0 1; margin: 0 2 1 2; }
#status { height: 1; color: #8f99a6; padding: 0 2; }
.user { color: #9fc3ff; padding: 1 0 0 0; }
.assistant { color: #f0f2f5; padding: 1 0 0 0; }
.tool { color: #8f99a6; padding: 0 0 0 2; }
.error { color: #ff8b8b; }
Input { border: none; background: transparent; }
"""


class TinyApp(App[None]):
    TITLE = "Tiny-CLI"
    SUB_TITLE = "The model decides. The runtime executes."
    CSS = CSS

    def __init__(
        self,
        provider: ProviderConfig | None = None,
        *,
        config_path: Path | None = None,
        plugins: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.provider = provider
        self.agent: Agent | None = None
        self.config_path = config_path
        self.plugins = list(plugins or [])
        self.busy = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield VerticalScroll(id="chat")
        yield Static(id="status")
        yield Container(Input(placeholder="Describe what you want to change…", id="composer"))
        yield Footer()

    def on_mount(self) -> None:
        status = self.query_one("#status", Static)
        if self.provider:
            self._activate(self.provider)
            if self.agent:
                self._add("assistant", "Tiny-CLI ready. Use /help for commands.")
        else:
            status.update("No provider configured")
            self._add("error", "No provider configured. Add ~/.config/tiny-cli/config.toml or set an API key environment variable.")
            self._add("assistant", "Run /help for commands.")
        self._add("tool", "Shell commands and file writes run without approval. Docker is recommended.")

    def _activate(self, provider: ProviderConfig) -> bool:
        try:
            agent = Agent(provider, self._event, plugins=self.plugins)
        except Exception as exc:
            self._add("error", f"{type(exc).__name__}: {exc}")
            return False
        if self.agent:
            self.agent.close()
        self.provider = provider
        self.agent = agent
        self.query_one("#status", Static).update(Text(f"{provider.name} · {provider.model} · plugins: {len(agent.plugins)}"))
        return True

    def on_unmount(self) -> None:
        if self.agent and not self.busy:
            self.agent.close()

    def _add(self, kind: str, text: str) -> None:
        chat = self.query_one("#chat", VerticalScroll)
        chat.mount(Static(Text(text), classes=kind))
        chat.scroll_end(animate=False)

    def _event(self, event: AgentEvent) -> None:
        if self.is_running:
            self.call_from_thread(self._handle_event, event)

    def _handle_event(self, event: AgentEvent) -> None:
        if event.kind == "assistant":
            self._add("assistant", event.text)
        elif event.kind == "tool_start":
            self._add("tool", f"↳ {event.tool}")
        elif event.kind == "tool_end":
            summary = event.text if len(event.text) <= 500 else event.text[:500] + "…"
            self._add("tool", summary)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return
        if self.busy and not prompt.startswith("/"):
            self._add("error", "A task is still running. Wait before sending another request.")
            return
        event.input.value = ""
        self._add("user", f"> {prompt}")
        if prompt.startswith("/"):
            self._command(prompt)
            return
        if not self.agent:
            self._add("error", "No provider configured.")
            return
        self.busy = True
        self.run_agent(self.agent, prompt)

    def _command(self, prompt: str) -> None:
        command, _, arg = prompt.partition(" ")
        if self.busy and command in {"/use", "/clear"}:
            self._add("error", "A task is still running. Wait before changing the session.")
            return
        if command in {"/q", "/quit", "/exit"}:
            self.exit()
        elif command == "/help":
            self._add("assistant", "/help   /providers (/models)   /use <provider> [model]   /plugins   /clear   /quit\n\n/use and /clear start a fresh session. Plugins run only when explicitly enabled.")
        elif command in {"/providers", "/models"}:
            try:
                providers = load_providers(self.config_path)
            except Exception as exc:
                self._add("error", f"{type(exc).__name__}: {exc}")
                return
            if not providers:
                self._add("assistant", "No providers configured.")
            else:
                self._add("assistant", "\n".join(f"{key} · {p.name} · {p.model} · {p.api_format}" for key, p in sorted(providers.items())))
        elif command == "/plugins":
            active = self.agent.plugins if self.agent else []
            self._add("assistant", "\n".join(active) if active else "No active plugins.")
        elif command == "/clear":
            if self.provider and self._activate(self.provider):
                self._add("assistant", "Started a fresh session.")
        elif command == "/use":
            name, _, model = arg.strip().partition(" ")
            if not name:
                self._add("error", "Usage: /use <provider> [model]")
                return
            try:
                provider = resolve_provider(name, model.strip() or None, self.config_path)
                if self._activate(provider):
                    self._add("assistant", f"Switched to {provider.name} · {provider.model}. Started a fresh session.")
            except Exception as exc:
                self._add("error", f"{type(exc).__name__}: {exc}")
        else:
            self._add("error", f"Unknown command: {command}")

    @work(thread=True, group="agent")
    def run_agent(self, agent: Agent, prompt: str) -> None:
        try:
            self.call_from_thread(self._add, "tool", "working…")
            agent.ask(prompt)
        except Exception as exc:
            if self.is_running:
                self.call_from_thread(self._add, "error", f"{type(exc).__name__}: {exc}")
        finally:
            if self.is_running:
                self.call_from_thread(self._finished)
            else:
                agent.close()

    def _finished(self) -> None:
        self.busy = False


def run(provider: ProviderConfig | None = None, *, config_path: Path | None = None, plugins: list[str] | None = None) -> None:
    TinyApp(provider, config_path=config_path, plugins=plugins).run()
