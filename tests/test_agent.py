import json
import sys
from types import ModuleType

import httpx
import pytest

from tiny_cli.agent import Agent
from tiny_cli.providers import ProviderConfig


def call(name, arguments, call_id="call_1"):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}


def client_for(replies, requests):
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": replies.pop(0)}]})
    return httpx.Client(transport=httpx.MockTransport(respond))


PROVIDER = ProviderConfig("test", "https://provider.test/v1", "", "test-model")


def test_default_request_has_only_user_history_and_four_tools(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "AGENTS.md").write_text("INSTRUCTIONS THAT MUST NOT BE INJECTED")
    requests = []
    with client_for([{"role": "assistant", "content": "done"}], requests) as client:
        agent = Agent(PROVIDER, client=client)
        assert agent.messages == []
        agent.ask("hello")
    assert requests[0]["messages"] == [{"role": "user", "content": "hello"}]
    assert {tool["function"]["name"] for tool in requests[0]["tools"]} == {
        "read_file", "write_file", "replace_in_file", "run_command",
    }
    assert agent.plugins == []


def test_multiple_tools_execute_and_full_results_return_to_model(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    requests, events = [], []
    text = "x" * 2000
    replies = [
        {"role": "assistant", "content": None, "tool_calls": [
            call("write_file", json.dumps({"path": "a.txt", "content": text})),
            call("read_file", '{"path":"a.txt"}', "call_2"),
        ]},
        {"role": "assistant", "content": "done"},
    ]
    with client_for(replies, requests) as client:
        Agent(PROVIDER, events.append, client=client).ask("write and read")
    assert (tmp_path / "a.txt").read_text() == text
    results = requests[1]["messages"][2:]
    assert [m["tool_call_id"] for m in results] == ["call_1", "call_2"]
    assert results[1]["content"] == text
    assert "_is_error" not in results[0]
    assert events[-1].kind == "turn_end"


@pytest.mark.parametrize("name,arguments", [
    ("read_file", "{"), ("read_file", "[]"), ("read_file", "{}"), ("unknown", "{}"),
])
def test_bad_tool_calls_return_errors_without_breaking_history(name, arguments):
    requests = []
    replies = [{"role": "assistant", "tool_calls": [call(name, arguments)]},
               {"role": "assistant", "content": "handled"}]
    with client_for(replies, requests) as client:
        Agent(PROVIDER, client=client).ask("test")
    assert requests[1]["messages"][-1]["content"].startswith("ERROR:")
    assert requests[1]["messages"][-1]["tool_call_id"] == "call_1"


def test_plugins_are_explicit_and_do_not_leak_between_agents(monkeypatch):
    module = ModuleType("test_optional_plugin")
    loads, events, requests = [], [], []

    def setup(agent):
        loads.append(agent)
        agent.add_tool({"type": "function", "function": {
            "name": "echo", "description": "Echo text.",
            "parameters": {"type": "object", "properties": {"text": {"type": "string"}}},
        }}, lambda text: text)
        def context(current):
            if current.messages[0]["role"] != "system":
                current.messages.insert(0, {"role": "system", "content": "opt-in context"})
        agent.before_request.append(context)
        agent.event_handlers.append(events.append)

    module.setup = setup
    monkeypatch.setitem(sys.modules, module.__name__, module)
    replies = [{"role": "assistant", "tool_calls": [call("echo", '{"text":"hello"}')]},
               {"role": "assistant", "content": "done"}]
    with client_for(replies, requests) as client:
        bare = Agent(PROVIDER, client=client)
        assert loads == []
        extended = Agent(PROVIDER, plugins=["test_optional_plugin:setup"] * 2, client=client)
        extended.ask("test")
        assert len(loads) == 1
        assert len(bare.tools) == 4 and bare.messages == []
        assert len(extended.tools) == 5
    assert requests[0]["messages"][0]["content"] == "opt-in context"
    assert requests[1]["messages"][-1]["content"] == "hello"
    assert events[-1].kind == "turn_end"


def test_missing_plugin_is_an_explicit_failure():
    with client_for([], []) as client:
        with pytest.raises(RuntimeError, match="Could not load plugin"):
            Agent(PROVIDER, plugins=["missing_tiny_test_plugin:setup"], client=client)


def test_http_errors_are_not_retried():
    requests = []
    def reject(request):
        requests.append(request)
        return httpx.Response(429)
    with httpx.Client(transport=httpx.MockTransport(reject)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            Agent(PROVIDER, client=client).ask("test")
    assert len(requests) == 1
