# Tiny-CLI

A deliberately tiny, model-driven coding CLI.

> **The model decides. The runtime executes.**

Tiny-CLI is an experiment in minimizing the coding-agent harness. The runtime provides a model with a small set of primitive tools and otherwise stays out of the way.

## What it does

The core loop is intentionally simple:

```text
User
  ↓
LLM
  ↓ tool call
Tiny-CLI
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

## What it intentionally does NOT do

Tiny-CLI deliberately has no:

- planner / plan mode
- subagents
- memory system
- MCP layer
- hooks
- automatic context selection
- repository map
- automatic retry policy
- model router
- permission heuristics
- hidden workflow rules

The goal is not to build the smartest harness. The goal is to make the harness as small and unopinionated as practical, so that improvements in the underlying model can express themselves directly.

## Safety

**Tiny-CLI has no built-in safety guardrails.** `run_command` executes shell commands with the privileges available to the process. This is intentional.

For repositories or workloads where the agent should be isolated, run Tiny-CLI inside a container or another OS-level sandbox. Do not give the agent credentials, mounts, or network access that you would not give to an arbitrary program.

Docker is an optional execution environment, not part of the agent core.

## Requirements

- Python 3.12+
- an OpenAI-compatible Responses API endpoint

## Local usage

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export TINY_CLI_API_KEY='your-key'
export TINY_CLI_MODEL='your-model'
# Optional for OpenAI-compatible providers:
# export TINY_CLI_BASE_URL='https://example.com/v1'

python tiny_cli.py
```

`OPENAI_API_KEY` is also accepted when `TINY_CLI_API_KEY` is not set.

## Docker

Build:

```bash
docker build -t tiny-cli .
```

Run against the current repository:

```bash
docker run --rm -it \
  -v "$PWD:/workspace" \
  -e TINY_CLI_API_KEY \
  -e TINY_CLI_MODEL \
  tiny-cli
```

For stronger isolation, additionally disable networking and drop unnecessary capabilities according to your environment. A container is not a universal security boundary; treat credentials and mounts as sensitive.

## Design principles

### 1. Model-first

The model owns planning, sequencing, diagnosis, retries, and strategy. Tiny-CLI does not try to be smarter than the model.

### 2. Primitive tools

Tools should expose capabilities rather than workflows. `run_command` is intentionally a primitive instead of a collection of specialized commands.

### 3. No hidden behavior

The runtime should not silently rewrite prompts, invent tasks, reroute requests, or repair the model's decisions.

### 4. Isolation outside the agent

Security policy belongs at the execution boundary: container, VM, sandbox, OS account, filesystem permissions, and network policy.

## Status

Early experimental project. The API adapter is intentionally narrow today. More functionality should only be added when it can be justified without turning the runtime into another opinionated agent framework.
