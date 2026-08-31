# OpenCode-like TUI and Provider Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Tiny-CLI into an installable terminal application with an OpenCode-like TUI while keeping the agent loop policy-light, and make arbitrary OpenAI-compatible providers easy to configure without changing agent code.

**Architecture:** The repository is split into four small responsibilities: `agent.py` owns the model/tool loop, `tools.py` owns four primitive filesystem/shell operations, `providers.py` resolves declarative provider configuration, and `tui.py` owns presentation and user commands. The runtime does not contain planner, subagent, memory, retry, routing, or permission orchestration; the model chooses tools and the executor returns results. Provider transport uses `httpx` against `/chat/completions`, so any compatible endpoint can be configured through TOML or environment variables.

**Tech Stack:** Python 3.12+, Textual, httpx, stdlib `tomllib`, OpenAI-compatible Chat Completions tool calling, pytest, Docker.

**Spec:** Installable `tiny` command; dark terminal UI with provider/model status, conversation log, tool activity, and input composer; provider configuration through environment variables or `~/.config/tiny-cli/config.toml`; four primitive tools; no planner, subagents, memory, hooks, hidden retries, model router, or permission heuristics; optional Docker isolation.

## Global Constraints

- The agent core must remain model-driven and policy-light.
- Provider configuration must support arbitrary OpenAI-compatible `base_url`, API-key environment variable, and model name.
- The TUI must not implement agent planning or retry behavior.
- The CLI must clearly warn that shell execution has no built-in safety guardrails.
- Docker is optional isolation, not an agent-core dependency.
- The console entrypoint must be `tiny` and `python -m tiny_cli` must remain runnable for smoke testing.

---

### Task 1: Core agent, tools, and provider transport

**Files:**
- Create: `tiny_cli/__init__.py`
- Create: `tiny_cli/__main__.py`
- Create: `tiny_cli/tools.py`
- Create: `tiny_cli/providers.py`
- Create: `tiny_cli/agent.py`
- Preserve/remove as appropriate: `tiny_cli.py` legacy prototype entrypoint
- Tests: `tests/test_tools.py`, `tests/test_providers.py`

- [x] Define `ProviderConfig(name, base_url, api_key_env, model)` and load arbitrary TOML providers.
- [x] Support built-in environment-variable shortcuts for OpenAI and OpenRouter without putting vendor logic into the agent loop.
- [x] Define exactly four primitive tools: `read_file`, `write_file`, `replace_in_file`, and `run_command`.
- [x] Execute tool calls directly and return raw tool results/errors to the model.
- [x] Implement a model loop over OpenAI-compatible Chat Completions; the loop stops when the model returns no tool calls.
- [x] Preserve `TINY_CLI_PROVIDER`, `TINY_CLI_MODEL`, `TINY_CLI_API_KEY`, and compatible provider environment variables.
- [x] Verify tool execution and arbitrary provider configuration with pytest.

### Task 2: Installable CLI and OpenCode-like TUI

**Files:**
- Create: `tiny_cli/tui.py`
- Create: `tiny_cli/app.py`
- Create: `pyproject.toml`
- Tests: `tests/test_config.py`

- [x] Expose the `tiny` console script through `pyproject.toml`.
- [x] Render a dark terminal UI with header/status, scrollable conversation, tool activity, and bottom composer using Textual.
- [x] Keep tool execution and agent decisions outside the TUI.
- [x] Show the current provider/model in the status bar.
- [x] Implement `/help`, `/models`, `/use <provider> [model]`, and `/quit`.
- [x] Allow the TUI to start even when no provider is configured so users can inspect help/configuration instead of crashing before the UI renders.
- [x] Add dedicated configuration tests covering CLI entrypoint parsing and no-provider startup behavior.
- [ ] Verify package import and CLI smoke command with the project dev environment.

### Task 3: Docker distribution and provider examples

**Files:**
- Create: `docker-compose.yml`
- Modify: `Dockerfile`
- Modify: `README.md`
- Create: `examples/config.toml`

- [x] Make the package executable from Docker with the `tiny` command.
- [x] Mount the working repository at `/workspace`.
- [x] Drop all Linux capabilities and enable `no-new-privileges` in the example Compose profile while keeping provider network access available for the remote model API.
- [x] Document OpenAI, OpenRouter, and generic OpenAI-compatible provider configuration without hardcoding vendor behavior into the agent.
- [x] Document the no-guardrail warning and recommend container/OS-level isolation for autonomous execution.
- [ ] Verify that package metadata, console entrypoint, Dockerfile, Compose environment names, and documented paths are internally consistent.

### Task 4: Repository verification and alignment

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/superpowers/plans/2026-09-01-opencode-like-tui-and-providers.md`

- [x] Add CI covering editable install, Python compilation, pytest, and `python -m tiny_cli --help`.
- [x] Keep this plan synchronized with the actual repository file layout and current implementation.
- [ ] Confirm the latest `main` commit has a successful GitHub Actions run before declaring the repository verified.
