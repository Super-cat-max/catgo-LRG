---
title: Chat System
description: CatBot — the in-app AI assistant for structure and workflow operations
source: src/lib/chat/ChatPane.svelte
---

# Chat System (CatBot)

**Source:** `src/lib/chat/`, `server/catgo/routers/chat.py`

CatBot is the in-app AI assistant. It uses a tool-calling LLM to drive structure manipulation, workflow construction, and analysis from natural-language instructions, with every tool call surfaced for inline approval before it runs.

## Architecture

```
┌────────────────────────────────────────┐
│  ChatPane.svelte                       │   UI: message list, input, permission cards
├────────────────────────────────────────┤
│  chat-state.svelte.ts                  │   Per-tab message history (persisted to localStorage)
├────────────────────────────────────────┤
│  sdk-stream.ts  +  llm-client.ts       │   SDK + HTTP transport to Claude / Codex / Gemini
├────────────────────────────────────────┤
│  tools.ts  +  workflow-tools.ts        │   Tool schemas exposed to the model
├────────────────────────────────────────┤
│  context.ts  +  rag.ts                 │   Structure-aware context and doc retrieval
└────────────────────────────────────────┘
```

### Components

- **`ChatPane.svelte`** — The chat UI: message list, input field, per-call `PermissionCard` for tool approval, `ToolProgressBlock` for in-flight tool execution feedback.
- **`chat-state.svelte.ts`** — Svelte 5 runes-based reactive state for conversation history. Messages are persisted per chat tab to `localStorage` (key: `catgo-chat-messages-{tab_id}`) and rehydrated on app launch.
- **`sdk-stream.ts`** — Streaming adapter for SDK-mode agents (Claude Agent SDK, Codex SDK, Gemini CLI SDK). Translates `user/tool_result` events into the in-app `tool_end` lifecycle.
- **`llm-client.ts`** — HTTP transport for direct-API mode (when no SDK is available or the user has set an API key directly).
- **`tools.ts` / `workflow-tools.ts`** — Tool schemas declared to the model: viewer controls, structure operations, workflow CRUD, file proposals.
- **`context.ts`** — Augments each LLM call with current viewer state (active structure, chemical formula, selected atoms) so responses are grounded in what the user is looking at.
- **`rag.ts`** — Optional retrieval over `docs-chunks.json` (a build artifact from `pnpm build:doc-chunks`) for doc-grounded answers.

## Provider Backends

CatBot supports three SDK-mode providers and direct-API fallback:

| Provider | How it connects | Setup |
|---|---|---|
| **Claude** (recommended) | Claude Agent SDK | Install [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) or set `ANTHROPIC_API_KEY` |
| **OpenAI Codex** | Codex SDK | Install [Codex CLI](https://github.com/openai/codex) or set `OPENAI_API_KEY` |
| **Gemini** | Gemini CLI SDK | Install [Gemini CLI](https://github.com/google-gemini/gemini-cli) or set `GEMINI_API_KEY` |

Provider selection happens per-chat-tab in the CatBot settings panel.

## Tool Execution and Permissions

Every tool call the model emits is intercepted and surfaced as a `PermissionCard` in the chat. The user approves each call individually before it runs — there is no auto-approval for destructive operations. Approved calls execute and stream their results back into the conversation as `tool_end` events.

Structure and workflow operations flow through the MCP server (`server/catgo/mcp_tools/`) and are exposed as `mcp__catgo__*` tools. See the [Workflow Tools module](/modules/ai/workflow-tools) for the full list.

## Server API

The chat backend lives at `server/catgo/routers/chat.py`. Endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/chat/stream` | `POST` | Stream a chat turn (Server-Sent Events) |
| `/chat/providers` | `GET` | List available LLM providers and their auth status |

## Related

- [Workflow Tools](/modules/ai/workflow-tools) — The MCP tools the model can call to build workflows
- [AI Chat Tutorial](/tutorials/ai/ai-chat) — How to start a conversation with CatBot
