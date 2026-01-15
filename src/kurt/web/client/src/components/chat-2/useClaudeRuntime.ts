/**
 * Claude Code Runtime Adapter for assistant-ui
 *
 * Connects to Claude Code via --output-format stream-json
 * and adapts the messages to assistant-ui's format.
 */

import { useCallback, useRef, useState } from 'react'

// Claude Code stream-json message types
interface ClaudeSystemMessage {
  type: 'system'
  subtype: 'init'
  session_id: string
  model: string
  tools: string[]
}

interface ClaudeAssistantMessage {
  type: 'assistant'
  message: {
    role: 'assistant'
    content: Array<
      | { type: 'text'; text: string }
      | { type: 'tool_use'; id: string; name: string; input: Record<string, unknown> }
    >
    stop_reason: string | null
  }
  session_id: string
}

interface ClaudeUserMessage {
  type: 'user'
  message: {
    role: 'user'
    content: Array<{
      type: 'tool_result'
      tool_use_id: string
      content: string
      is_error: boolean
    }>
  }
  tool_use_result?: {
    stdout: string
    stderr: string
  }
}

interface ClaudeResultMessage {
  type: 'result'
  subtype: 'success' | 'error'
  result: string
  total_cost_usd: number
  duration_ms: number
}

type ClaudeMessage = ClaudeSystemMessage | ClaudeAssistantMessage | ClaudeUserMessage | ClaudeResultMessage

// Parse NDJSON stream
function parseStreamLine(line: string): ClaudeMessage | null {
  if (!line.trim()) return null
  try {
    return JSON.parse(line)
  } catch {
    return null
  }
}

// Strip ANSI escape codes
function stripAnsi(text: string): string {
  return text.replace(/\x1b\[[0-9;]*[A-Za-z]/g, '')
}

export interface ClaudeRuntimeOptions {
  /** WebSocket URL for PTY connection */
  wsUrl?: string
  /** API endpoint for HTTP mode */
  apiUrl?: string
  /** Session ID to resume */
  sessionId?: string
}

/**
 * Hook to create a Claude Code runtime adapter
 */
export function useClaudeRuntime(options: ClaudeRuntimeOptions = {}) {
  const { wsUrl = '/ws/pty', apiUrl = '/api/claude' } = options

  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(options.sessionId ?? null)
  const [model, setModel] = useState<string>('claude-sonnet-4-20250514')

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => setIsConnected(true)
    ws.onclose = () => setIsConnected(false)
    ws.onerror = () => setIsConnected(false)

    return ws
  }, [wsUrl])

  // Runtime adapter for assistant-ui
  const adapter = {
    async *run({ messages, abortSignal }: {
      messages: Array<{ role: string; content: Array<{ type: string; text?: string }> }>
      abortSignal?: AbortSignal
    }) {
      const lastMessage = messages[messages.length - 1]
      const userText = lastMessage?.content?.find(c => c.type === 'text')?.text || ''

      if (!userText.trim()) return

      // For now, use HTTP streaming endpoint
      // TODO: Switch to WebSocket for bidirectional communication
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: userText,
          session_id: sessionId,
          output_format: 'stream-json'
        }),
        signal: abortSignal,
      })

      if (!response.ok) {
        yield { content: [{ type: 'text' as const, text: `Error: ${response.statusText}` }] }
        return
      }

      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''
      let currentText = ''
      let toolCalls: Array<{ id: string; name: string; input: Record<string, unknown> }> = []

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            const msg = parseStreamLine(line)
            if (!msg) continue

            if (msg.type === 'system' && msg.subtype === 'init') {
              setSessionId(msg.session_id)
              setModel(msg.model)
            }

            if (msg.type === 'assistant') {
              for (const content of msg.message.content) {
                if (content.type === 'text') {
                  currentText = content.text
                  yield { content: [{ type: 'text' as const, text: currentText }] }
                }
                if (content.type === 'tool_use') {
                  toolCalls.push({
                    id: content.id,
                    name: content.name,
                    input: content.input
                  })
                  // Yield tool use indicator
                  const toolText = `\n\n**Using tool: ${content.name}**\n\`\`\`json\n${JSON.stringify(content.input, null, 2)}\n\`\`\``
                  yield { content: [{ type: 'text' as const, text: currentText + toolText }] }
                }
              }
            }

            if (msg.type === 'user' && msg.tool_use_result) {
              // Show tool result
              const resultText = `\n\n**Tool result:**\n\`\`\`\n${stripAnsi(msg.tool_use_result.stdout || msg.tool_use_result.stderr || '')}\n\`\`\``
              currentText += resultText
              yield { content: [{ type: 'text' as const, text: currentText }] }
            }

            if (msg.type === 'result') {
              // Final result
              if (msg.result && msg.result !== currentText) {
                yield { content: [{ type: 'text' as const, text: msg.result }] }
              }
            }
          }
        }
      } finally {
        reader.releaseLock()
      }
    }
  }

  return {
    adapter,
    connect,
    isConnected,
    sessionId,
    model,
  }
}

export default useClaudeRuntime
