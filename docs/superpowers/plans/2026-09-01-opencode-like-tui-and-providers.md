# OpenCode-like TUI and Provider Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Tiny-CLI into an installable terminal application with an OpenCode-like chat UI while keeping the agent loop and policy surface minimal, and make arbitrary OpenAI-compatible providers easy to configure.

**Architecture:** Separate presentation, provider transport, tool execution, and the agent loop. The TUI owns interaction and rendering; the provider registry resolves a named provider/model to an OpenAI-compatible HTTP endpoint; the agent only alternates model requests and tool execution. Provider configuration is declarative TOML so adding a provider does not require changing agent code.

**Tech Stack:** Python 3.12+, Textual, httpx, TOML via stdlib `tomllib`/`tomli_w`, OpenAI-compatible Chat Completions tool calling, Docker.

**Spec:** The approved chat design: OpenCode-like terminal UI; installable `tiny` command; model/provider configuration through environment variables or `~/.config/tiny-cli/config.toml`; no planner, subagents, memory, hooks, hidden retries, or permission heuristics; optional Docker isolation.

## Global Constraints

- The agent core must remain model-driven and policy-light.
- Provider configuration must support arbitrary OpenAI-compatible `base_url`, API-key environment variable, and model name.
- The TUI must not implement agent planning or retry behavior.
- The CLI must clearly warn that shell execution has no built-in safety guardrails.
- Docker is optional isolation, not an agent-core dependency.

---

### Task 1: Split core into tools and provider transport

**Files:**
- Create: `tiny_cli/__init__.py`
- Create: `tiny_cli/tools.py`
- Create: `tiny_cli/providers.py`
- Create: `tiny_cli/agent.py`
- Modify: `tiny_cli.py`
- Test: `tests/test_providers.py`

- [ ] Add `ProviderConfig` and declarative config loading for arbitrary OpenAI-compatible endpoints.
- [ ] Add the four primitive tools and an executor with no policy layer.
- [ ] Add a model loop that sends the conversation, receives tool calls, executes them, and returns tool results.
- [ ] Preserve `TINY_CLI_*` environment variables for backward compatibility.
- [ ] Run import and provider configuration tests.

### Task 2: Add installable CLI and OpenCode-like TUI

**Files:**
- Create: `tiny_cli/tui.py`
- Create: `tiny_cli/app.py`
- Create: `pyproject.toml`
- Create: `tests/test_config.py`

- [ ] Expose a `tiny` console script.
- [ ] Render a dark terminal UI with header/status, scrollable conversation, tool activity, and bottom composer.
- [ ] Keep tool execution and agent decisions outside the TUI.
- [ ] Show current provider/model in status and expose simple slash commands for `/models`, `/help`, and `/quit`.
- [ ] Start with `tiny` directly; no separate subcommand required.
- [ ] Run configuration and package-import tests.

### Task 3: Docker distribution and provider examples

**Files:**
- Create: `docker-compose.yml`
- Modify: `Dockerfile`
- Modify: `README.md`
- Create: `examples/config.toml`

- [ ] Make the package executable from Docker with the same `tiny` command.
- [ ] Provide a compose profile that mounts `/workspace` and exposes no more privileges than necessary by default.
- [ ] Document OpenRouter, OpenAI, and generic OpenAI-compatible provider configuration without hardcoding vendor logic into the agent.
- [ ] Document the no-guardrail warning and container recommendation.
- [ ] Run a static smoke test that the package metadata, CLI entrypoint, and Docker files are internally consistent.
