from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import Agent


def load_plugins(agent: Agent, specs: list[str]) -> None:
    """Load only explicitly selected module:setup callables, in order."""
    for spec in dict.fromkeys(specs):
        module, separator, attribute = spec.partition(":")
        if not module or not separator or not attribute:
            raise ValueError(f"Invalid plugin '{spec}'; expected module:setup")
        try:
            setup = getattr(import_module(module), attribute)
            setup(agent)
        except Exception as exc:
            raise RuntimeError(f"Could not load plugin '{spec}': {exc}") from exc
