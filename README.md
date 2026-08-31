# Tiny-CLI

> **The model decides. The runtime executes.**

Tiny-CLI is a deliberately minimal coding agent with an OpenCode-like terminal UI. It keeps the agent harness small: the model chooses actions, Tiny-CLI exposes a few primitive tools, and the runtime executes them.

## Install

```bash
pipx install tiny-cli
# or
pip install tiny-cli
```

Then run:

```bash
tiny
```

The application opens directly in the terminal UI.

## Provider configuration

Tiny-CLI is not tied to OpenAI. Providers are declarative and use OpenAI-compatible **Chat Completions** endpoints. Add as many providers as you need to `~/.config/tiny-cli/config.toml`.

```toml
[providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
api_key_env = "OPENROUTER_API_KEY"
model = "openai/gpt-5"

[providers.deepseek]
name = "DeepSeek"
base_url = "https://api.deepseek.com/v1"
api_key_env = "DEEPSEEK_API_KEY"
model = "deepseek-chat"

[providers.my-provider]
name = "My Provider"
base_url = "https://example.com/v1"
api_key_env = "MY_PROVIDER_API_KEY"
model = "my-model"
```

No Tiny-CLI code changes are required to add a provider. Any service that speaks the OpenAI-compatible Chat Completions API can be configured this way.

Built-in environment shortcuts are also supported:

```bash
export OPENROUTER_API_KEY=...
export TINY_CLI_MODEL=openai/gpt-5
# then:
tiny --provider openrouter
```

Inside the UI:

```text
/help
/models
/use <provider> [model]
/quit
```

## What the runtime intentionally does NOT do

- planner / plan mode
- subagents
- memory system
- MCP orchestration
- hooks
- automatic context selection
- repository map
- hidden retry policy
- model routing
- permission heuristics
- workflow-specific correction logic

The goal is not to build the smartest harness. The goal is to keep the harness as small and unopinionated as practical so that improvements in the underlying model express themselves directly.

## Core loop

```text
User
  ↓
TUI
  ↓
LLM
  ↓ tool call
Tiny-CLI executor
  ↓
OS / repository
  ↓ result
LLM
```

Core tools:

- `read_file`
- `write_file`
- `replace_in_file`
- `run_command`

The agent loop is intentionally a thin request → tool execution → result loop. The model owns planning, sequencing, diagnosis, and retries.

## Safety

**Tiny-CLI has no built-in safety guardrails.** `run_command` executes shell commands with the privileges available to the process. This is intentional.

Run Tiny-CLI inside Docker, a VM, a dedicated OS account, or another sandbox when working with untrusted prompts or sensitive systems. Keep credentials and mounts to the minimum required.

Example:

```bash
docker build -t tiny-cli .
docker run --rm -it \
  -v "$PWD:/workspace" \
  -e OPENROUTER_API_KEY \
  -e TINY_CLI_PROVIDER=openrouter \
  -e TINY_CLI_MODEL=openai/gpt-5 \
  tiny-cli
```

The included `docker-compose.yml` drops Linux capabilities and enables `no-new-privileges` while retaining network access for the model provider. Stronger isolation should be applied by your deployment environment as appropriate.

## Development

```bash
git clone https://github.com/highsun9941/Tiny-CLI.git
cd Tiny-CLI
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest
```

## Design principles

### 1. Model-first

The model owns planning, sequencing, diagnosis, and retries. Tiny-CLI does not try to be smarter than the model.

### 2. Primitive tools

Tools expose capabilities rather than workflows. `run_command` is deliberately primitive instead of being replaced by a large collection of specialized coding commands.

### 3. No hidden behavior

The runtime should not silently rewrite prompts, invent tasks, reroute requests, or repair model decisions.

### 4. Providers outside the core

Provider credentials, base URLs, and model names live in configuration. The agent core knows how to call a provider interface, not vendor-specific workflow logic.

### 5. Isolation outside the agent

Security policy belongs at the execution boundary: container, VM, sandbox, OS account, filesystem permissions, and network policy.

## Status

Early experimental project. The UI and provider layer are intentionally separate from the agent loop. Features should only be added when they can be justified without turning Tiny-CLI into another opinionated agent framework.
