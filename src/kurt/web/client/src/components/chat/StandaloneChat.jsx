import { useState, useEffect, useRef, useCallback } from 'react'
import { chatThemeVars } from './ChatPanel'
import { assistantMessageStyles } from './AssistantMessage'
import TextBlock from './TextBlock'
import ToolUseBlock, { ToolOutput, ToolError } from './ToolUseBlock'
import BashToolRenderer from './BashToolRenderer'
import ReadToolRenderer from './ReadToolRenderer'
import WriteToolRenderer from './WriteToolRenderer'
import EditToolRenderer from './EditToolRenderer'
import GlobToolRenderer from './GlobToolRenderer'
import GrepToolRenderer from './GrepToolRenderer'
import PermissionPanel from './PermissionPanel'

/**
 * StandaloneChat - Simple chat UI that connects directly to Claude Code PTY
 * Access via ?poc=standalone in URL
 */

// Build WebSocket URL for stream-json connection
const buildWsUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  // Use stream-json endpoint for clean JSON communication
  return `${protocol}://${host}/ws/claude-stream`
}

// Strip ANSI escape codes and control characters
const stripAnsi = (text) => {
  if (!text) return ''
  // eslint-disable-next-line no-control-regex
  return text
    .replace(/\x1b\[[0-9;]*[A-Za-z]/g, '')       // CSI sequences
    .replace(/\x1b\][^\x07]*\x07/g, '')          // OSC sequences
    .replace(/\x1b\[\?[0-9]+[hl]/g, '')          // Private mode sequences
    .replace(/\x1b[()][AB012]/g, '')             // Character set sequences
    .replace(/\x1b=/g, '')                       // Application keypad
    .replace(/\x1b>/g, '')                       // Normal keypad
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, '') // Control chars except \n \r \t
}

// Clean response text from noise
const cleanResponse = (text) => {
  if (!text) return ''
  return text
    .replace(/-- INSERT --/g, '')
    .replace(/ctrl\+g to edit in VS Code/g, '')
    .replace(/^>\s*/gm, '')                      // Remove prompt chars
    .replace(/^\s*\n/gm, '')                     // Remove empty lines at start
    .trim()
}

// Render a single content block (text or tool_use)
const ContentBlockRenderer = ({ block, toolResults }) => {
  if (block.type === 'text') {
    return (
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
        <span style={{ color: '#858585', fontSize: '8px', lineHeight: '22px', flexShrink: 0, marginTop: '2px' }}>●</span>
        <div style={{ flex: 1 }}>
          <TextBlock text={block.text} />
        </div>
      </div>
    )
  }

  if (block.type === 'tool_use') {
    const toolName = block.name
    const input = block.input || {}
    const result = toolResults?.[block.id]
    const status = result ? 'complete' : 'running'

    // Parse result content if available
    let resultContent = null
    let resultError = null
    if (result) {
      try {
        if (typeof result.content === 'string') {
          resultContent = result.content
        } else if (Array.isArray(result.content)) {
          resultContent = result.content.map(c => c.text || '').join('\n')
        }
        if (result.is_error) {
          resultError = resultContent
          resultContent = null
        }
      } catch {
        resultContent = JSON.stringify(result)
      }
    }

    // Render specific tool types
    switch (toolName) {
      case 'Bash':
        return (
          <BashToolRenderer
            command={input.command}
            description={input.description}
            output={resultContent}
            error={resultError}
            status={status}
          />
        )

      case 'Read':
        return (
          <ReadToolRenderer
            filePath={input.file_path}
            content={resultContent}
            error={resultError}
            status={status}
          />
        )

      case 'Write':
        return (
          <WriteToolRenderer
            filePath={input.file_path}
            content={input.content}
            error={resultError}
            status={status}
          />
        )

      case 'Edit': {
        // Calculate line changes
        const oldLines = (input.old_string || '').split('\n').length
        const newLines = (input.new_string || '').split('\n').length
        const linesAdded = Math.max(0, newLines - oldLines)
        const linesRemoved = Math.max(0, oldLines - newLines)
        return (
          <EditToolRenderer
            filePath={input.file_path}
            oldContent={input.old_string}
            newContent={input.new_string}
            linesAdded={linesAdded || newLines}
            linesRemoved={linesRemoved}
            error={resultError}
            status={status}
          />
        )
      }

      case 'Glob':
        return (
          <GlobToolRenderer
            pattern={input.pattern}
            files={resultContent ? resultContent.split('\n').filter(Boolean) : []}
            error={resultError}
            status={status}
          />
        )

      case 'Grep':
        // Parse grep results into {file, matches} format
        const grepResults = resultContent
          ? resultContent.split('\n').filter(Boolean).map(line => {
              // Try to parse "file:line:content" format
              const match = line.match(/^([^:]+):(\d+):(.*)$/)
              if (match) {
                return { file: match[1], matches: [{ line: parseInt(match[2]), content: match[3] }] }
              }
              return { file: line, matches: [] }
            })
          : []
        return (
          <GrepToolRenderer
            pattern={input.pattern}
            path={input.path}
            results={grepResults}
            error={resultError}
            status={status}
          />
        )

      // Default tool rendering
      default:
        return (
          <ToolUseBlock
            toolName={toolName}
            description={JSON.stringify(input).slice(0, 60) + '...'}
            status={status}
          >
            {resultContent && (
              <ToolOutput>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                  {resultContent.length > 500 ? resultContent.slice(0, 500) + '...' : resultContent}
                </pre>
              </ToolOutput>
            )}
            {resultError && <ToolError message={resultError} />}
            {status === 'running' && (
              <div style={{ color: '#858585', fontSize: '13px', fontStyle: 'italic' }}>
                Running {toolName}...
              </div>
            )}
          </ToolUseBlock>
        )
    }
  }

  return null
}

export default function StandaloneChat() {
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [rawOutput, setRawOutput] = useState('')
  const [showRaw, setShowRaw] = useState(false)
  const [debugLog, setDebugLog] = useState([])

  // Slash commands and @ mentions
  const [showSlashMenu, setShowSlashMenu] = useState(false)
  const [slashFilter, setSlashFilter] = useState('')
  const [showAtMenu, setShowAtMenu] = useState(false)
  const [atFilter, setAtFilter] = useState('')
  const [selectedMenuIndex, setSelectedMenuIndex] = useState(0)

  // Plan mode
  const [isPlanMode, setIsPlanMode] = useState(false)
  const [planContent, setPlanContent] = useState('')

  // Permission requests
  const [pendingPermissions, setPendingPermissions] = useState([])

  // Command history
  const [commandHistory, setCommandHistory] = useState([])
  const [historyIndex, setHistoryIndex] = useState(-1)

  // Track message finalization to prevent duplicates
  const messageIdRef = useRef(0)
  const finalizedRef = useRef(false)

  const socketRef = useRef(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const currentResponseRef = useRef('')
  const currentBlocksRef = useRef([])       // Track content blocks being streamed
  const currentBlockIndexRef = useRef(-1)   // Track current block index
  const toolResultsRef = useRef({})         // Map tool_use_id -> result
  const lastSentMessageRef = useRef('')
  const stateRef = useRef('idle') // idle, waiting_echo, streaming
  const responseTimeoutRef = useRef(null)

  // Slash commands configuration
  const SLASH_COMMANDS = [
    { command: '/help', description: 'Show available commands' },
    { command: '/clear', description: 'Clear conversation history' },
    { command: '/compact', description: 'Compact conversation context' },
    { command: '/config', description: 'View/edit configuration' },
    { command: '/cost', description: 'Show token usage and costs' },
    { command: '/doctor', description: 'Check Claude Code health' },
    { command: '/init', description: 'Initialize project with CLAUDE.md' },
    { command: '/login', description: 'Switch Anthropic accounts' },
    { command: '/logout', description: 'Sign out from Anthropic' },
    { command: '/memory', description: 'Edit CLAUDE.md memory files' },
    { command: '/model', description: 'Switch AI model' },
    { command: '/permissions', description: 'View allowed tools' },
    { command: '/plan', description: 'Enter plan mode' },
    { command: '/review', description: 'Review code changes' },
    { command: '/terminal-setup', description: 'Install shell integration' },
    { command: '/vim', description: 'Enter vim mode for editing' },
  ]

  // @ mention types
  const AT_TYPES = [
    { type: '@file', icon: '📄', description: 'Reference a file' },
    { type: '@folder', icon: '📁', description: 'Reference a folder' },
    { type: '@code', icon: '💻', description: 'Reference code symbol' },
    { type: '@url', icon: '🔗', description: 'Reference a URL' },
    { type: '@git', icon: '🔀', description: 'Reference git state' },
  ]

  // Filter slash commands based on input
  const filteredSlashCommands = SLASH_COMMANDS.filter(cmd =>
    cmd.command.toLowerCase().includes(slashFilter.toLowerCase())
  )

  // Filter @ types based on input
  const filteredAtTypes = AT_TYPES.filter(at =>
    at.type.toLowerCase().includes(atFilter.toLowerCase())
  )

  // Connect to WebSocket
  useEffect(() => {
    const url = buildWsUrl()
    console.log('[WS] Connecting to:', url)

    const socket = new WebSocket(url)
    socketRef.current = socket

    socket.onopen = () => {
      console.log('[WS] Connected')
      // Connection state will be set when we receive 'system' -> 'connected' message
    }

    socket.onmessage = (event) => {
      const data = event.data

      // Log raw output
      setRawOutput(prev => prev + data + '\n')

      // Parse JSON message from stream bridge
      try {
        const msg = JSON.parse(data)
        handleStreamMessage(msg)
      } catch {
        console.log('[WS] Non-JSON message:', data)
      }
    }

    socket.onclose = (event) => {
      console.log('[WS] Closed:', event.code, event.reason)
      setIsConnected(false)
    }

    socket.onerror = (err) => {
      console.error('[WS] Error:', err)
    }

    return () => {
      socket.close()
    }
  }, [])

  // Handle stream-json messages from Claude Code
  const handleStreamMessage = useCallback((msg) => {
    // Debug log
    setDebugLog(prev => [...prev.slice(-50), { ts: Date.now(), msg }])

    const msgType = msg.type

    switch (msgType) {
      case 'system':
        // System messages (connected, error, etc.)
        console.log('[Claude] System:', msg.subtype, msg.message)
        if (msg.subtype === 'connected') {
          setIsConnected(true)
        }
        break

      case 'assistant':
        // Skip assistant snapshots - we use streaming deltas instead
        // These are sent multiple times and cause duplicates
        break

      case 'content_block_start':
        // Start of a new content block
        currentBlockIndexRef.current = msg.index ?? currentBlocksRef.current.length
        const newBlock = msg.content_block || { type: 'text', text: '' }

        // Expand blocks array if needed
        while (currentBlocksRef.current.length <= currentBlockIndexRef.current) {
          currentBlocksRef.current.push({ type: 'text', text: '' })
        }
        currentBlocksRef.current[currentBlockIndexRef.current] = { ...newBlock }

        // For text blocks, initialize current text
        if (newBlock.type === 'text') {
          currentResponseRef.current = newBlock.text || ''
        }
        updateStreamingMessage()
        break

      case 'content_block_delta':
        // Streaming delta
        if (msg.delta?.type === 'text_delta' && msg.delta?.text) {
          // Text delta
          currentResponseRef.current += msg.delta.text
          const idx = currentBlockIndexRef.current
          if (idx >= 0 && currentBlocksRef.current[idx]) {
            currentBlocksRef.current[idx] = {
              ...currentBlocksRef.current[idx],
              text: currentResponseRef.current
            }
          }
          updateStreamingMessage()
        } else if (msg.delta?.type === 'input_json_delta' && msg.delta?.partial_json) {
          // Tool input streaming - accumulate JSON
          const idx = currentBlockIndexRef.current
          if (idx >= 0 && currentBlocksRef.current[idx]) {
            const block = currentBlocksRef.current[idx]
            block._partialJson = (block._partialJson || '') + msg.delta.partial_json
            // Try to parse partial JSON for display
            try {
              block.input = JSON.parse(block._partialJson)
            } catch {
              // Not valid JSON yet, keep accumulating
            }
            currentBlocksRef.current[idx] = { ...block }
          }
          updateStreamingMessage()
        }
        break

      case 'content_block_stop':
        // End of content block - reset for next block
        currentResponseRef.current = ''
        break

      case 'message_stop':
      case 'message_delta':
        // Message complete - only finalize once
        if ((msg.type === 'message_stop' || msg.delta?.stop_reason) && !finalizedRef.current) {
          finalizedRef.current = true
          finalizeStreamingMessage()
        }
        break

      case 'result':
        // Final result or exit - finalize the streaming message (only once)
        if (msg.subtype === 'exit') {
          console.log('[Claude] Process exited:', msg.exit_code)
          setIsConnected(false)
        }
        if (!finalizedRef.current) {
          finalizedRef.current = true
          finalizeStreamingMessage()
        }
        if (msg.result && currentBlocksRef.current.length === 0) {
          // Only show result if we don't have blocks
          const resultText = typeof msg.result === 'string'
            ? msg.result
            : JSON.stringify(msg.result, null, 2)
          setMessages(prev => [...prev, {
            id: `result-${Date.now()}`,
            role: 'assistant',
            contentBlocks: [{ type: 'text', text: resultText }]
          }])
        }
        break
      case 'control_request': {
        const request = msg.request || {}
        const toolName = request.tool_name || request.toolName || 'tool'
        const toolInput = request.input || request.tool_input || request.inputs || {}
        const permissionSuggestions = request.permission_suggestions || request.suggestions || []
        const blockedPath = request.blocked_path || request.blockedPath || ''
        const requestId = msg.request_id || `control-${Date.now()}`
        const nextPermission = {
          id: requestId,
          tool_name: toolName,
          tool_input: toolInput,
          blocked_path: blockedPath,
          permission_suggestions: permissionSuggestions,
        }
        setPendingPermissions((prev) => [
          ...prev.filter((perm) => perm.id !== requestId),
          nextPermission,
        ])
        break
      }
      case 'control_cancel_request': {
        const requestId = msg.request_id
        if (!requestId) {
          setPendingPermissions([])
          break
        }
        setPendingPermissions((prev) => prev.filter((perm) => perm.id !== requestId))
        break
      }

      case 'tool_result':
        // Tool execution result - store for rendering
        if (msg.tool_use_id) {
          toolResultsRef.current = {
            ...toolResultsRef.current,
            [msg.tool_use_id]: {
              content: msg.content,
              is_error: msg.is_error
            }
          }
          // Force re-render of streaming message to show result
          updateStreamingMessage()
        }
        break

      case 'raw':
        // Raw non-JSON output
        console.log('[Claude] Raw:', msg.data)
        break

      default:
        console.log('[Claude] Unknown message type:', msgType, msg)
    }
  }, [])

  // Helper to update streaming message
  const updateStreamingMessage = useCallback(() => {
    const blocks = [...currentBlocksRef.current]
    if (blocks.length === 0) return

    setMessages(prev => {
      const filtered = prev.filter(m => m.id !== 'streaming')
      return [...filtered, {
        id: 'streaming',
        role: 'assistant',
        contentBlocks: blocks,
        toolResults: { ...toolResultsRef.current },
        isStreaming: true
      }]
    })
  }, [])

  // Helper to finalize streaming message
  const finalizeStreamingMessage = useCallback(() => {
    const blocks = [...currentBlocksRef.current]

    // Prevent double finalization
    if (blocks.length === 0) {
      setIsStreaming(false)
      return
    }

    // Check if we already finalized (no streaming message exists)
    setMessages(prev => {
      const hasStreaming = prev.some(m => m.id === 'streaming')
      if (!hasStreaming) {
        return prev // Already finalized
      }

      const filtered = prev.filter(m => m.id !== 'streaming')
      return [...filtered, {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        contentBlocks: blocks,
        toolResults: { ...toolResultsRef.current }
      }]
    })

    // Reset refs for next message
    currentBlocksRef.current = []
    currentBlockIndexRef.current = -1
    currentResponseRef.current = ''
    setIsStreaming(false)
  }, [])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Send message
  const handleSend = useCallback(() => {
    const text = inputValue.trim()
    if (!text || !socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return

    // Add user message to UI
    setMessages(prev => [...prev, {
      id: `user-${Date.now()}`,
      role: 'user',
      text
    }])

    // Send via stream-json protocol
    socketRef.current.send(JSON.stringify({
      type: 'user',
      message: text
    }))

    // Save to history
    setCommandHistory(prev => [...prev, text])
    setHistoryIndex(-1)

    // Reset state for new message
    currentResponseRef.current = ''
    currentBlocksRef.current = []
    currentBlockIndexRef.current = -1
    finalizedRef.current = false
    messageIdRef.current += 1
    setIsStreaming(true)
    setInputValue('')
  }, [inputValue])

  // Stop/cancel streaming
  const handleStop = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      // Send interrupt signal (Ctrl+C equivalent)
      socketRef.current.send(JSON.stringify({
        type: 'interrupt'
      }))
    }
    // Finalize current message as interrupted
    if (currentBlocksRef.current.length > 0) {
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== 'streaming')
        return [...filtered, {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          contentBlocks: [...currentBlocksRef.current],
          toolResults: { ...toolResultsRef.current },
          interrupted: true
        }]
      })
    }
    currentBlocksRef.current = []
    currentBlockIndexRef.current = -1
    currentResponseRef.current = ''
    setIsStreaming(false)
  }, [])

  // Handle permission grant
  const handlePermissionDecision = useCallback((permission, option) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      const decision = option?.decision
      if (decision === 'dismiss') {
        setPendingPermissions(prev => prev.filter(p => p.id !== permission.id))
        return
      }
      // Send control response
      const response = {
        type: 'control_response',
        request_id: permission.id,
        decision,
        tool_input: permission.tool_input || {}
      }
      if (option?.updatedInput) {
        response.updatedInput = option.updatedInput
      }
      if (option?.permissionSuggestions) {
        response.permission_suggestions = option.permissionSuggestions
      }
      if (option?.message) {
        response.message = option.message
      }
      socketRef.current.send(JSON.stringify(response))
    }
    // Remove from pending
    setPendingPermissions(prev => prev.filter(p => p.id !== permission.id))
  }, [])

  // Handle input change with slash/@ detection
  const handleInputChange = (e) => {
    const value = e.target.value
    setInputValue(value)

    // Detect slash commands (at start of input)
    if (value.startsWith('/')) {
      setShowSlashMenu(true)
      setSlashFilter(value)
      setSelectedMenuIndex(0)
      setShowAtMenu(false)
    } else {
      setShowSlashMenu(false)
    }

    // Detect @ mentions
    const atMatch = value.match(/@(\w*)$/)
    if (atMatch) {
      setShowAtMenu(true)
      setAtFilter(atMatch[0])
      setSelectedMenuIndex(0)
      setShowSlashMenu(false)
    } else {
      setShowAtMenu(false)
    }
  }

  // Handle slash command selection
  const handleSlashSelect = (command) => {
    if (command === '/clear') {
      setMessages([])
      setInputValue('')
    } else if (command === '/plan') {
      setIsPlanMode(true)
      setInputValue('')
      // Notify Claude we're entering plan mode
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({
          type: 'user',
          message: '/plan'
        }))
      }
    } else {
      // Send as message to Claude
      setInputValue('')
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        setMessages(prev => [...prev, { id: `user-${Date.now()}`, role: 'user', text: command }])
        socketRef.current.send(JSON.stringify({ type: 'user', message: command }))
        setIsStreaming(true)
      }
    }
    setShowSlashMenu(false)
  }

  // Handle @ mention selection
  const handleAtSelect = (atType) => {
    // Replace the @partial with the selected type and add space
    const newValue = inputValue.replace(/@\w*$/, atType.type + ' ')
    setInputValue(newValue)
    setShowAtMenu(false)
    inputRef.current?.focus()
  }

  // Handle keyboard navigation in menus
  const handleKeyDown = (e) => {
    const activeMenu = showSlashMenu ? filteredSlashCommands : showAtMenu ? filteredAtTypes : null
    const menuLength = activeMenu?.length || 0

    // Escape to stop streaming or close menus
    if (e.key === 'Escape') {
      if (isStreaming) {
        e.preventDefault()
        handleStop()
        return
      }
      if (showSlashMenu || showAtMenu) {
        setShowSlashMenu(false)
        setShowAtMenu(false)
        return
      }
      if (isPlanMode) {
        setIsPlanMode(false)
        return
      }
    }

    // Menu navigation
    if (activeMenu && menuLength > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedMenuIndex(prev => (prev + 1) % menuLength)
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedMenuIndex(prev => (prev - 1 + menuLength) % menuLength)
        return
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault()
        if (showSlashMenu) {
          handleSlashSelect(filteredSlashCommands[selectedMenuIndex].command)
        } else if (showAtMenu) {
          handleAtSelect(filteredAtTypes[selectedMenuIndex])
        }
        return
      }
    }

    // Command history navigation (when no menu is open)
    if (!activeMenu && commandHistory.length > 0) {
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        const newIndex = historyIndex < commandHistory.length - 1 ? historyIndex + 1 : historyIndex
        setHistoryIndex(newIndex)
        setInputValue(commandHistory[commandHistory.length - 1 - newIndex] || '')
        return
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        const newIndex = historyIndex > 0 ? historyIndex - 1 : -1
        setHistoryIndex(newIndex)
        setInputValue(newIndex >= 0 ? commandHistory[commandHistory.length - 1 - newIndex] : '')
        return
      }
    }

    // Normal enter to send
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      <style>{chatThemeVars}</style>
      <style>{assistantMessageStyles}</style>
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        .standalone-chat {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: #1e1e1e;
          color: #ccc;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .chat-header {
          padding: 12px 16px;
          border-bottom: 1px solid #333;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
        }
        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }
        .status-dot.connected { background: #89d185; }
        .status-dot.disconnected { background: #f48771; }
        .toggle-raw {
          background: #333;
          border: none;
          color: #ccc;
          padding: 6px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
        }
        .toggle-raw:hover { background: #444; }
        .chat-body {
          flex: 1;
          display: flex;
          overflow: hidden;
        }
        .messages-area {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
        }
        .raw-area {
          width: 400px;
          border-left: 1px solid #333;
          overflow-y: auto;
          padding: 12px;
          font-family: monospace;
          font-size: 11px;
          white-space: pre-wrap;
          word-break: break-all;
          background: #111;
          color: #888;
        }
        .message {
          margin-bottom: 16px;
        }
        .user-msg {
          display: inline-block;
          background: #393937;
          padding: 8px 14px;
          border-radius: 12px;
          max-width: 80%;
        }
        .assistant-msg {
          display: flex;
          gap: 8px;
        }
        .assistant-msg .bullet {
          color: #858585;
          font-size: 8px;
          line-height: 24px;
        }
        .assistant-msg.streaming .bullet {
          color: #ae5630;
        }
        .assistant-msg .text {
          flex: 1;
          line-height: 1.6;
          white-space: pre-wrap;
        }
        .cursor {
          display: inline-block;
          width: 2px;
          height: 16px;
          background: #ccc;
          margin-left: 2px;
          animation: blink 1s step-end infinite;
        }
        .input-area {
          padding: 12px 16px;
          border-top: 1px solid #333;
        }
        .input-row {
          display: flex;
          gap: 8px;
          background: #3c3c3c;
          border-radius: 8px;
          padding: 8px 12px;
        }
        .input-row textarea {
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          color: #ccc;
          font-size: 14px;
          font-family: inherit;
          resize: none;
        }
        .send-btn {
          background: #ae5630;
          color: white;
          border: none;
          border-radius: 6px;
          width: 32px;
          height: 32px;
          cursor: pointer;
          font-size: 16px;
        }
        .send-btn:disabled {
          background: #555;
          cursor: default;
        }
        .streaming-indicator {
          font-size: 12px;
          color: #858585;
          margin-top: 8px;
        }
        /* Autocomplete menus */
        .autocomplete-menu {
          position: absolute;
          bottom: 100%;
          left: 0;
          right: 0;
          background: #2d2d2d;
          border: 1px solid #454545;
          border-radius: 8px;
          margin-bottom: 8px;
          max-height: 300px;
          overflow-y: auto;
          box-shadow: 0 -4px 12px rgba(0,0,0,0.3);
        }
        .autocomplete-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 14px;
          cursor: pointer;
          border-bottom: 1px solid #333;
        }
        .autocomplete-item:last-child {
          border-bottom: none;
        }
        .autocomplete-item:hover,
        .autocomplete-item.selected {
          background: #3c3c3c;
        }
        .autocomplete-item .cmd {
          font-family: var(--font-mono, monospace);
          color: #e6b450;
          font-weight: 500;
        }
        .autocomplete-item .desc {
          color: #858585;
          font-size: 13px;
        }
        .autocomplete-item .icon {
          font-size: 16px;
        }
        /* Plan mode */
        .plan-mode-banner {
          background: linear-gradient(90deg, #ae5630 0%, #8b4513 100%);
          color: white;
          padding: 8px 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 13px;
        }
        .plan-mode-banner .label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 500;
        }
        .plan-mode-banner button {
          background: rgba(255,255,255,0.2);
          border: none;
          color: white;
          padding: 4px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
        }
        .plan-mode-banner button:hover {
          background: rgba(255,255,255,0.3);
        }
        .input-area.plan-mode {
          border-top: 2px solid #ae5630;
        }
        .input-area.plan-mode .input-row {
          border: 1px solid #ae5630;
        }
        /* Stop button */
        .stop-btn {
          background: #f48771;
          color: white;
          border: none;
          border-radius: 6px;
          padding: 6px 12px;
          cursor: pointer;
          font-size: 12px;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .stop-btn:hover {
          background: #e5765f;
        }
        /* Permission panel */
        .permission-panel {
          background: #2d2d2d;
          border: 1px solid #454545;
          border-radius: 8px;
          padding: 12px 16px;
          margin: 8px 0;
        }
        .permission-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
          color: #cca700;
          font-weight: 500;
        }
        .permission-details {
          background: #1e1e1e;
          border-radius: 4px;
          padding: 8px 12px;
          margin-bottom: 12px;
          font-family: var(--font-mono, monospace);
          font-size: 12px;
          color: #858585;
          max-height: 150px;
          overflow: auto;
        }
        .permission-actions {
          display: flex;
          gap: 8px;
        }
        .permission-btn {
          padding: 6px 16px;
          border-radius: 4px;
          border: none;
          cursor: pointer;
          font-size: 13px;
          font-weight: 500;
        }
        .permission-btn.allow {
          background: #89d185;
          color: #1e1e1e;
        }
        .permission-btn.allow:hover {
          background: #7ac275;
        }
        .permission-btn.deny {
          background: #3c3c3c;
          color: #ccc;
        }
        .permission-btn.deny:hover {
          background: #4a4a4a;
        }
      `}</style>

      <div className="standalone-chat">
        <div className="chat-header">
          <div className="status">
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
            <span>{isConnected ? 'Connected to Claude Code' : 'Disconnected'}</span>
          </div>
          <button className="toggle-raw" onClick={() => setShowRaw(!showRaw)}>
            {showRaw ? 'Hide Raw' : 'Show Raw'}
          </button>
        </div>

        <div className="chat-body">
          <div className="messages-area">
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', color: '#666', marginTop: '40px' }}>
                <div style={{ fontSize: '32px', marginBottom: '16px' }}>✨</div>
                <div>Send a message to start chatting with Claude Code</div>
              </div>
            )}

            {messages.map(msg => (
              <div key={msg.id} className="message">
                {msg.role === 'user' ? (
                  <div className="user-msg">{msg.text}</div>
                ) : (
                  <div className={`assistant-msg ${msg.isStreaming ? 'streaming' : ''}`}>
                    {/* Render content blocks if available */}
                    {msg.contentBlocks ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
                        {msg.contentBlocks.map((block, idx) => (
                          <ContentBlockRenderer
                            key={`${msg.id}-block-${idx}`}
                            block={block}
                            toolResults={msg.toolResults}
                          />
                        ))}
                        {msg.isStreaming && (
                          <span className="cursor" style={{ marginLeft: '16px' }} />
                        )}
                      </div>
                    ) : (
                      /* Legacy: plain text rendering */
                      <>
                        <span className="bullet">●</span>
                        <div className="text">
                          <TextBlock text={msg.text} />
                          {msg.isStreaming && <span className="cursor" />}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {showRaw && (
            <div className="raw-area">
              <strong>Debug Log:</strong>
              <hr style={{ border: 'none', borderTop: '1px solid #333', margin: '8px 0' }} />
              {debugLog.length === 0 ? '(waiting for messages...)' : debugLog.slice(-20).map((entry, i) => (
                <div key={i} style={{ marginBottom: '8px', borderBottom: '1px solid #222', paddingBottom: '8px' }}>
                  <div style={{ color: '#666', fontSize: '10px' }}>
                    {new Date(entry.ts).toLocaleTimeString()} | state: {entry.state}
                  </div>
                  <div style={{ color: '#8a8', fontSize: '11px' }}>cleaned: {JSON.stringify(entry.cleaned)}</div>
                </div>
              ))}
              <hr style={{ border: 'none', borderTop: '1px solid #333', margin: '8px 0' }} />
              <strong>Raw PTY Output:</strong>
              <hr style={{ border: 'none', borderTop: '1px solid #333', margin: '8px 0' }} />
              <div style={{ maxHeight: '300px', overflow: 'auto' }}>
                {rawOutput || '(waiting for output...)'}
              </div>
            </div>
          )}
        </div>

        {/* Plan mode banner */}
        {isPlanMode && (
          <div className="plan-mode-banner">
            <div className="label">
              <span>📋</span>
              <span>Plan Mode</span>
              <span style={{ fontWeight: 'normal', opacity: 0.8 }}>— Claude will create a plan before implementing</span>
            </div>
            <button onClick={() => setIsPlanMode(false)}>Exit Plan Mode</button>
          </div>
        )}

        <div className={`input-area ${isPlanMode ? 'plan-mode' : ''}`}>
          <div style={{ position: 'relative' }}>
            {/* Slash command menu */}
            {showSlashMenu && filteredSlashCommands.length > 0 && (
              <div className="autocomplete-menu">
                {filteredSlashCommands.map((cmd, idx) => (
                  <div
                    key={cmd.command}
                    className={`autocomplete-item ${idx === selectedMenuIndex ? 'selected' : ''}`}
                    onClick={() => handleSlashSelect(cmd.command)}
                  >
                    <span className="cmd">{cmd.command}</span>
                    <span className="desc">{cmd.description}</span>
                  </div>
                ))}
              </div>
            )}

            {/* @ mention menu */}
            {showAtMenu && filteredAtTypes.length > 0 && (
              <div className="autocomplete-menu">
                {filteredAtTypes.map((at, idx) => (
                  <div
                    key={at.type}
                    className={`autocomplete-item ${idx === selectedMenuIndex ? 'selected' : ''}`}
                    onClick={() => handleAtSelect(at)}
                  >
                    <span className="icon">{at.icon}</span>
                    <span className="cmd">{at.type}</span>
                    <span className="desc">{at.description}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="input-row">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder={isPlanMode ? 'Describe what you want to plan...' : isConnected ? 'Type a message... (/ for commands, @ for mentions)' : 'Connecting...'}
                disabled={!isConnected}
                rows={1}
              />
              <button
                className="send-btn"
                onClick={handleSend}
                disabled={!inputValue.trim() || !isConnected}
              >
                ↑
              </button>
            </div>
          </div>
          {/* Permission requests */}
          {pendingPermissions.length > 0 && (
            <div style={{ marginBottom: '8px' }}>
              {pendingPermissions.map((perm, idx) => (
                <div key={perm.id || idx} className="permission-panel">
                  <PermissionPanel
                    title={perm.title}
                    options={perm.options}
                    diff={perm.diff}
                    filePath={perm.file_path}
                    toolName={perm.tool_name}
                    toolInput={perm.tool_input}
                    blockedPath={perm.blocked_path}
                    permissionSuggestions={perm.permission_suggestions}
                    onSelect={(option) => handlePermissionDecision(perm, option)}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Streaming indicator with stop button */}
          {isStreaming && (
            <div className="streaming-indicator" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <span style={{ color: '#ae5630', marginRight: '6px' }}>✳</span>
                <span style={{ color: '#b48ead' }}>Crunching…</span>
                <span style={{ color: '#858585', marginLeft: '4px' }}>(thinking)</span>
              </div>
              <button className="stop-btn" onClick={handleStop}>
                <span>■</span> Stop
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
