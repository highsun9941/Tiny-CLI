from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path.home() / ".config" / "tiny-cli" / "config.toml"


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    model: str
    api_format: str = "openai"
    max_tokens: int = 4096

    def __post_init__(self) -> None:
        if self.api_format not in {"openai", "anthropic"}:
            raise ValueError(f"Unknown API format: {self.api_format}")
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("Provider base_url must start with http:// or https://")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Provider model must be a nonempty string")
        if type(self.max_tokens) is not int or self.max_tokens <= 0:
            raise ValueError("Provider max_tokens must be a positive integer")

    def api_key(self) -> str:
        if not self.api_key_env:
            return ""
        value = os.getenv(self.api_key_env)
        if not value:
            raise RuntimeError(f"Missing API key environment variable: {self.api_key_env}")
        return value


def _builtins() -> dict[str, ProviderConfig]:
    providers: dict[str, ProviderConfig] = {}
    if os.getenv("OPENAI_API_KEY") or os.getenv("TINY_CLI_API_KEY"):
        providers["openai"] = ProviderConfig("OpenAI", os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1", "TINY_CLI_API_KEY" if os.getenv("TINY_CLI_API_KEY") else "OPENAI_API_KEY", os.getenv("TINY_CLI_MODEL") or "gpt-5")
    if os.getenv("OPENROUTER_API_KEY"):
        providers["openrouter"] = ProviderConfig("OpenRouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", os.getenv("TINY_CLI_MODEL") or "openai/gpt-5")
    return providers


def load_config(path: Path | None = None) -> dict[str, Any]:
    explicit_path = path is not None or bool(os.getenv("TINY_CLI_CONFIG"))
    path = path or Path(os.getenv("TINY_CLI_CONFIG") or DEFAULT_CONFIG)
    if path.exists():
        return tomllib.loads(path.read_text(encoding="utf-8"))
    if explicit_path:
        raise FileNotFoundError(f"Config file not found: {path}")
    return {}


def _configured_providers(data: dict[str, Any]) -> dict[str, ProviderConfig]:

    providers = _builtins()
    for key, raw in data.get("providers", {}).items():
        providers[key] = ProviderConfig(
            name=raw.get("name", key),
            base_url=raw["base_url"].rstrip("/"),
            api_key_env=raw.get("api_key_env", "OPENAI_API_KEY"),
            model=raw["model"],
            api_format=raw.get("api_format", "openai"),
            max_tokens=raw.get("max_tokens", 4096),
        )
    return providers


def load_providers(path: Path | None = None) -> dict[str, ProviderConfig]:
    return _configured_providers(load_config(path))


class NoProviderError(RuntimeError):
    pass


def resolve_provider(
    provider_name: str | None = None,
    model: str | None = None,
    path: Path | None = None,
) -> ProviderConfig:
    data = load_config(path)
    providers = _configured_providers(data)
    name = provider_name or os.getenv("TINY_CLI_PROVIDER") or data.get("default_provider")
    model = model or os.getenv("TINY_CLI_MODEL")
    if name:
        if name not in providers:
            available = ", ".join(sorted(providers)) or "none"
            raise RuntimeError(f"Unknown provider '{name}'. Available: {available}")
        provider = providers[name]
        return replace(provider, model=model or provider.model)
    if not providers:
        raise NoProviderError("No provider configured. Add one to ~/.config/tiny-cli/config.toml or set a supported API key environment variable.")
    first = providers[sorted(providers)[0]]
    return replace(first, model=model or first.model)
