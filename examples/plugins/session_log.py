"""Opt-in example: save completed turns as JSON Lines in the working directory."""
import json
from pathlib import Path


def setup(agent):
    def on_event(event):
        if event.kind == "turn_end":
            with Path("tiny-session.jsonl").open("a", encoding="utf-8") as output:
                output.write(json.dumps(agent.messages, ensure_ascii=False) + "\n")

    agent.event_handlers.append(on_event)
