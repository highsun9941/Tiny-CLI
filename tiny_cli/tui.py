from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Header, Input, Static
from textual.worker import Worker

from .agent import Agent, AgentEvent
from .providers import ProviderConfig, load_providers


CSS = """
Screen { background: #0b0d10; color: #e6e8eb; }
Header { background: #11151a; color: #e6e8eb; }
#chat { height: 1fr; padding: 1 2; scrollbar-size: 1 1; }
#composer { height: auto; border: round #303842; padding: 0 1; margin: 0 2 1 2; }
#status { height: 1; color: #8f99a6; padding: 0 2; }
.user { color: #d7e3ff; padding: 1 0 0 0; }
.assistant { color: #f0f2f5; padding: 1 0 0 0; }
.tool { color: #8f99a6; padding: 0 0 0 2; }
.error { color: #ff8b8b; }

Input { border: none; background: transparent; }
"""


class TinyApp(App[None]):
    TITLE = "Tiny-CLI"
    SUB_TITLE = "The model decides. The runtime executes."
    CSS = CSS

    def __init__(self, provider: ProviderConfig | None = None) -> None:
        super().__init__()
        self.provider = provider
        self.agent: Agent | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield VerticalScroll(id="chat")
        yield Static(id="status")
        yield Container(Input(placeholder="Describe what you want to change…", id="composer"))
        yield Footer()

    def on_mount(self) -> None:
        status = self.query_one("#status", Static)
        if self.provider:
            status.update(f"{self.provider.name} · {self.provider.model}")
            self.agent = Agent(self.provider, self._event)
            self._add("assistant", "Tiny-CLI ready. The runtime has no planner, subagents, or permission heuristics.")
        else:
            status.update("No provider configured")
            self._add("error", "No provider configured. Add ~/.config/tiny-cli/config.toml or set an API key environment variable.")
            self._add("assistant", "Run /help for commands. Providers are configured without changing Tiny-CLI code.")

    def _add(self, kind: str, text: str) -> None:
        chat = self.query_one("#chat", VerticalScroll)
        cls = kind
        chat.mount(Static(text, classes=cls))
        chat.scroll_end(animate=False)

    def _event(self, event: AgentEvent) -> None:
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
        event.input.value = ""
        if not prompt:
            return
        self._add("user", f"> {prompt}")
        if prompt.startswith("/"):
            self._command(prompt)
            return
        if not self.agent:
            self._add("error", "No provider configured.")
            return
        self.run_agent(prompt)

    def _command(self, prompt: str) -> None:
        command, _, arg = prompt.partition(" ")
        if command in {"/q", "/quit", "/exit"}:
            self.exit()
        elif command == "/help":
            self._add("assistant", "/help  /models  /quit\n\nProvider config: ~/.config/tiny-cli/config.toml")
        elif command == "/models":
            providers = load_providers()
            if not providers:
                self._add("assistant", "No providers configured.")
            else:
                self._add("assistant", "\n".join(f"{key} · {p.name} · {p.model}" for key, p in sorted(providers.items())))
        else:
            self._add("error", f"Unknown command: {command}")

    async def run_agent(self, prompt: str) -> None:
        if not self.agent:
            return
        self._add("tool", "working…")
        try:
            await self.agent.ask(prompt)  # type: ignore[misc]
        except Exception as exc:
            self._add("error", f"{type(exc).__name__}: {exc}")


def run(provider: ProviderConfig | None = None) -> None:
    TinyApp(provider).run()
