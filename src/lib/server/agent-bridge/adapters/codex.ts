import type { AgentAdapter } from '../adapter.js'
import { registerAdapter } from '../adapter.js'
import type { AgentEvent, SessionInfo, StreamParams } from '../types.js'

// ---------------------------------------------------------------------------
// Helper: translate a single Codex SDK event to zero or more AgentEvents
// ---------------------------------------------------------------------------

// Per-thread incremental-text tracking. The Codex SDK emits item.updated with
// `item.text` containing the FULL accumulated text so far (not a delta), so
// the adapter has to diff against the last seen text per item to surface
// chunked output. State is keyed by `item.id` and cleared opportunistically
// on item.completed.
const _item_text_seen = new Map<string, string>()

function emit_text_delta(itemId: string, fullText: string): string | null {
  const prev = _item_text_seen.get(itemId) ?? ''
  if (!fullText || fullText === prev) return null
  const delta = fullText.startsWith(prev) ? fullText.slice(prev.length) : fullText
  _item_text_seen.set(itemId, fullText)
  return delta || null
}

function* translateEvent(evt: any): Generator<AgentEvent> {
  const type: string = evt?.type ?? ''

  // Codex SDK ≥0.117 ThreadEvent union:
  //   thread.started | turn.started | turn.completed | turn.failed |
  //   item.started | item.updated | item.completed | error
  // Item payloads (evt.item.type):
  //   agent_message | reasoning | command_execution | file_change |
  //   mcp_tool_call | web_search | todo_list | error

  // ── thread.started ─────────────────────────────────────────────────────────
  if (type === 'thread.started') {
    yield { type: 'status', sessionId: evt.thread_id }
    return
  }

  // ── item.started / item.updated → text deltas + tool_start ────────────────
  if (type === 'item.started' || type === 'item.updated') {
    const item = evt.item ?? {}
    const item_type: string = item.type ?? ''
    const item_id: string = item.id ?? ''

    if (item_type === 'agent_message' || item_type === 'reasoning') {
      const delta = emit_text_delta(item_id, item.text ?? '')
      if (delta) yield { type: 'text', text: delta }
      return
    }
    if (type === 'item.started') {
      if (item_type === 'command_execution') {
        yield {
          type: 'tool_start',
          toolId: item_id,
          toolName: 'bash',
          input: { command: item.command ?? '' },
        }
        return
      }
      if (item_type === 'mcp_tool_call') {
        yield {
          type: 'tool_start',
          toolId: item_id,
          toolName: `${item.server ?? 'mcp'}.${item.tool ?? ''}`,
          input: item.arguments ?? {},
        }
        return
      }
    }
    return
  }

  // ── item.completed → flush trailing text, close tools ─────────────────────
  if (type === 'item.completed') {
    const item = evt.item ?? {}
    const item_type: string = item.type ?? ''
    const item_id: string = item.id ?? ''

    if (item_type === 'agent_message' || item_type === 'reasoning') {
      const delta = emit_text_delta(item_id, item.text ?? '')
      if (delta) yield { type: 'text', text: delta }
      _item_text_seen.delete(item_id)
      return
    }
    if (item_type === 'command_execution') {
      const isError = item.exit_code !== undefined && item.exit_code !== 0
      yield {
        type: 'tool_end',
        toolId: item_id,
        toolName: 'bash',
        result: item.aggregated_output ?? '',
        isError,
      }
      return
    }
    if (item_type === 'mcp_tool_call') {
      const isError = item.status === 'failed'
      const output = item.result?.content ?? item.error?.message ?? ''
      yield {
        type: 'tool_end',
        toolId: item_id,
        toolName: `${item.server ?? 'mcp'}.${item.tool ?? ''}`,
        result: typeof output === 'string' ? output : JSON.stringify(output),
        isError,
      }
      return
    }
    if (item_type === 'error') {
      yield { type: 'result', isError: true, errorMessage: item.message }
      yield { type: 'done' }
      return
    }
    return
  }

  // ── turn.completed → emit result with usage ───────────────────────────────
  if (type === 'turn.completed') {
    const usage = evt.usage
    yield {
      type: 'result',
      isError: false,
      usage: usage
        ? {
            input_tokens: usage.input_tokens ?? 0,
            output_tokens: usage.output_tokens ?? 0,
            cache_read_input_tokens: usage.cached_input_tokens,
          }
        : undefined,
    }
    return
  }

  // ── turn.failed / error → surface error ───────────────────────────────────
  if (type === 'turn.failed' || type === 'error') {
    const msg = evt.error?.message ?? evt.message ?? 'Unknown Codex error'
    yield { type: 'result', isError: true, errorMessage: msg }
    yield { type: 'done' }
    return
  }
}

// ---------------------------------------------------------------------------
// CodexAdapter
// ---------------------------------------------------------------------------

export function createCodexAdapter(): AgentAdapter {
  return {
    agent: 'codex',

    async *stream(params: StreamParams): AsyncGenerator<AgentEvent> {
      const { prompt, sessionId, model, cwd, abortSignal } = params

      // Dynamic import — the package may not be installed everywhere.
      const { Codex } = (await import('@openai/codex-sdk')) as any

      const codex = new Codex({ model: model ?? undefined }) as any

      const thread = sessionId
        ? (codex.resumeThread(sessionId) as any)
        : (codex.startThread() as any)

      const abortController = new AbortController()
      if (abortSignal) {
        abortSignal.addEventListener('abort', () =>
          abortController.abort(abortSignal.reason),
        )
      }

      // SDK ≥ 0.117 returns `Promise<StreamedTurn>` where the event stream
      // lives on `.events` (AsyncGenerator<ThreadEvent>). Previously the call
      // was treated as if it already returned the iterable, producing
      // "streamIterable is not async iterable".
      const streamedTurn = await thread.runStreamed(prompt, {
        abortController,
        cwd: cwd ?? undefined,
        approvalPolicy: 'on-request',
      })
      const streamIterable = streamedTurn.events as AsyncIterable<any>

      let resultEmitted = false

      for await (const evt of streamIterable) {
        for (const agentEvent of translateEvent(evt)) {
          yield agentEvent
          if (agentEvent.type === 'done') resultEmitted = true
        }
      }

      // Ensure we always close the stream with a result + done pair even if
      // the SDK didn't emit a terminal event.
      if (!resultEmitted) {
        yield { type: 'result', isError: false }
        yield { type: 'done' }
      }
    },

    async listSessions(): Promise<SessionInfo[]> {
      // The Codex SDK does not expose a session listing API at this time.
      return []
    },
  }
}

// Self-register at module load time.
registerAdapter('codex', createCodexAdapter)
