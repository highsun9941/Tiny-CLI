from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path.home() / ".config" / "tiny-cli" / "config.toml"


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    model: str

    def api_key(self) -> str:
        value = os.getenv(self.api_key_env)
        if not value:
            raise RuntimeError(f"Missing API key environment variable: {self.api_key_env}")
        return value


def _builtins() -> dict[str, ProviderConfig]:
    providers: dict[str, ProviderConfig] = {}
    if os.getenv("OPENAI_API_KEY") or os.getenv("TINY_CLI_API_KEY"):
        providers["openai"] = ProviderConfig("OpenAI", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), "TINY_CLI_API_KEY" if os.getenv("TINY_CLI_API_KEY") else "OPENAI_API_KEY", os.getenv("TINY_CLI_MODEL", "gpt-5"))
    if os.getenv("OPENROUTER_API_KEY"):
        providers["openrouter"] = ProviderConfig("OpenRouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", os.getenv("TINY_CLI_MODEL", "openai/gpt-5"))
    return providers


def load_providers(path: Path | None = None) -> dict[str, ProviderConfig]:
    path = path or DEFAULT_CONFIG
    data: dict[str, Any] = {}
    if path.exists():
        data = tomllib.loads(path.read_text(encoding="utf-8"))

    providers = _builtins()
    for key, raw in data.get("providers", {}).items():
        providers[key] = ProviderConfig(
            name=raw.get("name", key),
            base_url=raw["base_url"].rstrip("/"),
            api_key_env=raw.get("api_key_env", "OPENAI_API_KEY"),
            model=raw["model"],
        )
    return providers


def resolve_provider(provider_name: str | None = None, model: str | None = None) -> ProviderConfig:
    providers = load_providers()
    name = provider_name or os.getenv("TINY_CLI_PROVIDER")
    if name:
        if name not in providers:
            available = ", ".join(sorted(providers)) or "none"
            raise RuntimeError(f"Unknown provider '{name}'. Available: {available}")
        provider = providers[name]
        return ProviderConfig(provider.name, provider.base_url, provider.api_key_env, model or provider.model)
    if not providers:
        raise RuntimeError("No provider configured. Add one to ~/.config/tiny-cli/config.toml or set a supported API key environment variable.")
    first = providers[sorted(providers)[0]]
    return ProviderConfig(first.name, first.base_url, first.api_key_env, model or first.model)
