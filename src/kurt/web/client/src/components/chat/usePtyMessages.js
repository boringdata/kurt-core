import { useState, useCallback, useRef } from 'react'

/**
 * usePtyMessages - Parse PTY output stream into chat messages
 *
 * State machine:
 * IDLE → USER_INPUT (after we send) → ASSISTANT_RESPONSE (after echo)
 *
 * Message boundaries:
 * - User message: text we sent via WebSocket
 * - Assistant start: after user input echo completes
 * - Assistant end: when new user input is sent
 */

// Strip ANSI escape codes from text
const stripAnsi = (text) => {
  // eslint-disable-next-line no-control-regex
  return text.replace(/\x1b\[[0-9;]*[A-Za-z]/g, '')
}

// Detect if output looks like a prompt (Claude waiting for input)
const isPromptLine = (text) => {
  const stripped = stripAnsi(text).trim()
  // Claude Code shows ">" or similar prompt indicators
  return stripped === '>' || stripped.endsWith('>')
}

export function usePtyMessages() {
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const stateRef = useRef('idle') // 'idle' | 'user_input' | 'assistant'
  const pendingUserInputRef = useRef('')
  const currentAssistantTextRef = useRef('')
  const messageIdRef = useRef(0)

  // Called when user sends input
  const onUserInput = useCallback((text) => {
    // Handle Enter key - finalize user message (MUST be checked before control char skip)
    if (text === '\r' || text === '\n') {
      if (pendingUserInputRef.current.trim()) {
        const userText = pendingUserInputRef.current.trim()
        const id = `user-${++messageIdRef.current}`

        setMessages((prev) => [
          ...prev,
          {
            id,
            role: 'user',
            content: [{ type: 'text', text: userText }],
          },
        ])

        stateRef.current = 'user_input'
        pendingUserInputRef.current = ''
        currentAssistantTextRef.current = ''
        setIsStreaming(true)
      }
      return
    }

    // Skip other control characters (arrows, etc.) - after Enter check
    if (text.length === 1 && text.charCodeAt(0) < 32) {
      return
    }

    // Handle backspace
    if (text === '\u007f' || text === '\b') {
      pendingUserInputRef.current = pendingUserInputRef.current.slice(0, -1)
      return
    }

    // Accumulate input
    pendingUserInputRef.current += text
  }, [])

  // Called when PTY sends output
  const onPtyOutput = useCallback((data) => {
    const text = typeof data === 'string' ? data : data.toString()

    // In user_input state, we're waiting for echo to complete
    if (stateRef.current === 'user_input') {
      // Look for newline after echo - assistant response starts
      if (text.includes('\n') || text.includes('\r')) {
        stateRef.current = 'assistant'
      }
      return
    }

    // In assistant state, accumulate response
    if (stateRef.current === 'assistant') {
      const cleanText = stripAnsi(text)

      // Check if this looks like a new prompt (end of response)
      if (isPromptLine(text)) {
        // Finalize assistant message
        if (currentAssistantTextRef.current.trim()) {
          const id = `assistant-${++messageIdRef.current}`
          const finalText = currentAssistantTextRef.current.trim()

          setMessages((prev) => [
            ...prev,
            {
              id,
              role: 'assistant',
              content: [{ type: 'text', text: finalText }],
            },
          ])
        }

        currentAssistantTextRef.current = ''
        stateRef.current = 'idle'
        setIsStreaming(false)
        return
      }

      // Accumulate assistant text
      currentAssistantTextRef.current += cleanText

      // Update streaming message in place
      if (currentAssistantTextRef.current.trim()) {
        const streamingId = 'assistant-streaming'
        const streamingText = currentAssistantTextRef.current.trim()

        setMessages((prev) => {
          // Remove any existing streaming message
          const filtered = prev.filter((m) => m.id !== streamingId)
          return [
            ...filtered,
            {
              id: streamingId,
              role: 'assistant',
              content: [{ type: 'text', text: streamingText }],
              isStreaming: true,
            },
          ]
        })
      }
    }
  }, [])

  // Called when history is received (on connect/resume)
  const onHistory = useCallback((historyText) => {
    // Only set history message if we don't have any messages yet
    // This prevents wiping out user messages during conversation
    setMessages((prev) => {
      if (prev.length === 0) {
        return [
          {
            id: 'history',
            role: 'assistant',
            content: [{ type: 'text', text: '[Session history loaded]' }],
          },
        ]
      }
      return prev
    })
  }, [])

  // Reset messages
  const reset = useCallback(() => {
    setMessages([])
    setIsStreaming(false)
    stateRef.current = 'idle'
    pendingUserInputRef.current = ''
    currentAssistantTextRef.current = ''
  }, [])

  return {
    messages,
    isStreaming,
    onUserInput,
    onPtyOutput,
    onHistory,
    reset,
  }
}

export default usePtyMessages
