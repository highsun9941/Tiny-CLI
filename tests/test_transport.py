import json

import httpx

from tiny_cli.agent import Agent
from tiny_cli.providers import ProviderConfig


def test_anthropic_round_trip_preserves_blocks_and_groups_tool_results(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TEST_ANTHROPIC_KEY", "test-key")
    native_blocks = [
        {"type": "thinking", "thinking": "test", "signature": "opaque-signature"},
        {"type": "text", "text": "Running commands."},
        {"type": "tool_use", "id": "a", "name": "run_command", "input": {"command": "printf hello > a.txt"}},
        {"type": "tool_use", "id": "b", "name": "run_command", "input": {}},
    ]
    replies = [{"content": native_blocks}, {"content": [{"type": "text", "text": "done"}]}]
    requests = []
    def respond(request):
        assert request.url == "https://anthropic.test/v1/messages"
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        assert "authorization" not in request.headers
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=replies.pop(0))
    provider = ProviderConfig("Claude", "https://anthropic.test/v1", "TEST_ANTHROPIC_KEY", "test-model", "anthropic", 1234)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        Agent(provider, client=client).ask("test")
    assert "system" not in requests[0]
    assert requests[0]["max_tokens"] == 1234
    assert [tool["name"] for tool in requests[0]["tools"]] == ["run_command"]
    assert "input_schema" in requests[0]["tools"][0]
    assert requests[1]["messages"][1] == {"role": "assistant", "content": native_blocks}
    results = requests[1]["messages"][2]
    assert results["role"] == "user"
    assert [block["tool_use_id"] for block in results["content"]] == ["a", "b"]
    assert not results["content"][0]["is_error"]
    assert results["content"][1]["is_error"]
    assert (tmp_path / "a.txt").read_text() == "hello"


def test_openai_transport_uses_custom_endpoint_and_optional_auth(monkeypatch):
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "done"}}]})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        Agent(ProviderConfig("local", "http://localhost:1234/v1/", "", "local-model"), client=client).ask("test")
        monkeypatch.setenv("CUSTOM_KEY", "test-key")
        Agent(ProviderConfig("remote", "https://custom.test/api/v1/", "CUSTOM_KEY", "remote-model"), client=client).ask("test")
    assert requests[0].url == "http://localhost:1234/v1/chat/completions"
    assert "authorization" not in requests[0].headers
    assert requests[1].url == "https://custom.test/api/v1/chat/completions"
    assert requests[1].headers["authorization"] == "Bearer test-key"
