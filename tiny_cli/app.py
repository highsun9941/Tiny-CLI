from __future__ import annotations

import argparse

from .providers import resolve_provider
from .tui import run


def main() -> int:
    parser = argparse.ArgumentParser(prog="tiny", description="A deliberately tiny, model-driven coding CLI")
    parser.add_argument("--provider", help="configured provider name")
    parser.add_argument("--model", help="override configured model")
    args = parser.parse_args()

    try:
        provider = resolve_provider(args.provider, args.model)
    except RuntimeError:
        provider = None
    run(provider)
    return 0
