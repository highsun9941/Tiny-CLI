from __future__ import annotations

import argparse
from pathlib import Path

from .providers import NoProviderError, load_config, resolve_provider
from .tui import run


def main() -> int:
    parser = argparse.ArgumentParser(prog="tiny", description="A deliberately tiny, model-driven coding CLI")
    parser.add_argument("--provider", help="configured provider name")
    parser.add_argument("--model", help="override configured model")
    parser.add_argument("--config", type=Path, help="provider and plugin configuration file")
    parser.add_argument("--plugin", action="append", default=[], metavar="MODULE:SETUP", help="enable an installed plugin (repeatable)")
    parser.add_argument("--no-plugins", action="store_true", help="disable all configured and command-line plugins")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        plugins = [] if args.no_plugins else config.get("plugins", {}).get("enabled", [])
        if not isinstance(plugins, list) or not all(isinstance(spec, str) for spec in plugins):
            raise ValueError("plugins.enabled must be a list of module:setup strings")
        if not args.no_plugins:
            plugins = list(dict.fromkeys([*plugins, *args.plugin]))
        try:
            provider = resolve_provider(args.provider, args.model, args.config)
        except NoProviderError:
            provider = None
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, AttributeError) as exc:
        parser.error(str(exc))
    run(provider, config_path=args.config, plugins=plugins)
    return 0
