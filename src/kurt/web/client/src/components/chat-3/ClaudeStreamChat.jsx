import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AssistantIf,
  AssistantRuntimeProvider,
  useLocalRuntime,
  MessagePrimitive,
  ComposerPrimitive,
  useComposer,
  useAssistantApi,
  useMessage,
  useThread,
} from '@assistant-ui/react'
import ChatPanel, { chatThemeVars } from '../chat/ChatPanel'
import MessageList, { Messages, EmptyState } from '../chat/MessageList'
import TextBlock from '../chat/TextBlock'
import SessionHeader from '../chat/SessionHeader'
import BashToolRenderer from '../chat/BashToolRenderer'
import ReadToolRenderer from '../chat/ReadToolRenderer'
import WriteToolRenderer from '../chat/WriteToolRenderer'
import EditToolRenderer from '../chat/EditToolRenderer'
import GlobToolRenderer from '../chat/GlobToolRenderer'
import GrepToolRenderer from '../chat/GrepToolRenderer'
import ToolUseBlock, { ToolOutput } from '../chat/ToolUseBlock'
import PermissionPanel from '../chat/PermissionPanel'
import { assistantMessageStyles } from '../chat/AssistantMessage'
import './styles.css'

const SLASH_COMMANDS = [
  { id: 'help', label: '/help', description: 'Show available commands' },
  { id: 'clear', label: '/clear', description: 'Clear the chat' },
  { id: 'compact', label: '/compact', description: 'Compact conversation' },
  { id: 'init', label: '/init', description: 'Initialize project' },
  { id: 'cost', label: '/cost', description: 'Show token usage' },
  { id: 'model', label: '/model', description: 'Switch AI model' },
  { id: 'config', label: '/config', description: 'Open settings' },
  { id: 'terminal', label: '/terminal', description: 'Switch to CLI mode' },
  { id: 'permissions', label: '/permissions', description: 'Manage permissions' },
  { id: 'memory', label: '/memory', description: 'Manage memory/context' },
]

const getApiBase = () => {
  const apiUrl = import.meta.env.VITE_API_URL || ''
  return apiUrl ? apiUrl.replace(/\/$/, '') : ''
}

const buildWsUrl = (sessionId, mode, forceNew = false) => {
  const apiUrl = import.meta.env.VITE_API_URL || ''
  const queryParams = new URLSearchParams()
  if (sessionId) queryParams.set('session_id', sessionId)
  if (mode) queryParams.set('mode', mode)
  if (forceNew) queryParams.set('force_new', '1')
  const params = queryParams.toString() ? `?${queryParams.toString()}` : ''
  if (apiUrl) {
    const url = new URL(apiUrl)
    const protocol = url.protocol === 'https:' ? 'wss' : 'ws'
    return `${protocol}://${url.host}/ws/claude-stream${params}`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  return `${protocol}://${host}/ws/claude-stream${params}`
}

const fetchSessions = async () => {
  try {
    const res = await fetch(`${getApiBase()}/api/sessions`)
    if (!res.ok) return []
    const data = await res.json()
    return data.sessions || []
  } catch {
    return []
  }
}

const searchFiles = async (query) => {
  if (!query || query.length < 1) return []
  try {
    const res = await fetch(`${getApiBase()}/api/search?q=${encodeURIComponent(query)}`)
    if (!res.ok) return []
    const data = await res.json()
    return (data.results || []).map((f) => ({
      id: f.path,
      label: f.name,
      path: f.path,
      dir: f.dir,
    }))
  } catch {
    return []
  }
}

const createNewSession = async () => {
  try {
    const res = await fetch(`${getApiBase()}/api/sessions`, { method: 'POST' })
    if (!res.ok) return null
    const data = await res.json()
    return data.session_id
  } catch {
    return null
  }
}

const fetchPendingApprovals = async () => {
  try {
    const res = await fetch(`${getApiBase()}/api/approval/pending`)
    if (!res.ok) return []
    const data = await res.json()
    return data.requests || []
  } catch {
    return []
  }
}

const submitApprovalDecision = async (requestId, decision, reason) => {
  try {
    const res = await fetch(`${getApiBase()}/api/approval/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: requestId, decision, reason }),
    })
    return res.ok
  } catch {
    return false
  }
}

const mergeStreamText = (previous, incoming) => {
  if (!previous) return incoming
  if (incoming.startsWith(previous)) return incoming
  if (previous.startsWith(incoming)) return previous
  return previous + incoming
}

const extractImagesFromText = (text, imageCache) => {
  if (!text) return { text: '', images: [] }
  const images = []
  let cleaned = text
  const dataUrlRegex = /!\[[^\]]*\]\((data:image\/[^)]+)\)/g
  let match
  while ((match = dataUrlRegex.exec(text)) !== null) {
    images.push(match[1])
  }
  const tokenRegex = /\[\[image:([^\]]+)\]\]/g
  while ((match = tokenRegex.exec(text)) !== null) {
    const cached = imageCache?.[match[1]]
    if (cached?.dataUrl) {
      images.push(cached.dataUrl)
    }
  }
  cleaned = cleaned.replace(dataUrlRegex, '').replace(tokenRegex, '').trim()
  return { text: cleaned, images }
}

const dataUrlToImagePart = (dataUrl) => {
  const match = /^data:(.*?);base64,(.*)$/.exec(dataUrl || '')
  if (!match) return null
  return {
    type: 'image',
    source: {
      type: 'base64',
      media_type: match[1],
      data: match[2],
    },
  }
}

const parseGrepResults = (output) => {
  if (!output) return []
  return output
    .split('\n')
    .filter(Boolean)
    .map((line) => {
      const match = line.match(/^(.*?):(\d+):(.*)$/)
      if (!match) return { file: 'output', matches: [{ line: 1, content: line }] }
      return {
        file: match[1],
        matches: [{ line: Number(match[2]), content: match[3] }],
      }
    })
}

const parseGlobFiles = (output) => {
  if (!output) return []
  return output
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

const ToolFallback = ({ name, input, output }) => {
  return (
    <ToolUseBlock
      toolName={name}
      description={input ? 'Custom tool input' : undefined}
      status="complete"
      collapsible={Boolean(output)}
      defaultExpanded={true}
    >
      {input && (
        <ToolOutput>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(input, null, 2)}
          </pre>
        </ToolOutput>
      )}
      {output && (
        <ToolOutput style={{ marginTop: '8px' }}>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{output}</pre>
        </ToolOutput>
      )}
    </ToolUseBlock>
  )
}

const useClaudeStreamRuntime = (
  currentSessionId,
  setCurrentSessionId,
  mode,
  contextFiles,
  clearContextFiles,
  onStreamingChange,
  onLastMessageChange,
  imageCache
) => {
  const wsRef = useRef(null)
  const queueRef = useRef([])
  const waitersRef = useRef([])
  const modeRef = useRef(mode)
  const contextFilesRef = useRef(contextFiles)
  const clearContextFilesRef = useRef(clearContextFiles)
  const imageCacheRef = useRef(imageCache)
  const [sessionName, setSessionName] = useState('New conversation')
  const [isConnected, setIsConnected] = useState(false)

  // Keep refs updated
  useEffect(() => {
    modeRef.current = mode
  }, [mode])
  useEffect(() => {
    contextFilesRef.current = contextFiles
  }, [contextFiles])
  useEffect(() => {
    clearContextFilesRef.current = clearContextFiles
  }, [clearContextFiles])
  useEffect(() => {
    imageCacheRef.current = imageCache
  }, [imageCache])

  const lastModeRef = useRef(null)

  const connect = useCallback((sessionId, connectMode) => {
    const useMode = connectMode || modeRef.current
    // Check if mode changed - need force_new to restart Claude with new --permission-mode
    const modeChanged = lastModeRef.current !== null && lastModeRef.current !== useMode
    lastModeRef.current = useMode

    // Close existing connection if switching sessions or mode
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close()
    }

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(buildWsUrl(sessionId, useMode, modeChanged))
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        resolve(ws)
      }
      ws.onclose = () => setIsConnected(false)
      ws.onerror = (event) => {
        setIsConnected(false)
        reject(event)
      }
      ws.onmessage = (event) => {
        let payload = null
        try {
          payload = JSON.parse(event.data)
        } catch {
          return
        }

        if (payload.type === 'system' && payload.subtype === 'connected' && payload.session_id) {
          setSessionName(payload.session_id)
          setCurrentSessionId(payload.session_id)
        }

        const queue = queueRef.current
        if (queue) {
          queue.push(payload)
          const waiter = waitersRef.current.shift()
          if (waiter) waiter()
        }
      }
    })
  }, [setCurrentSessionId])

  const nextPayload = useCallback(async () => {
    if (queueRef.current.length) return queueRef.current.shift()
    return new Promise((resolve) => {
      waitersRef.current.push(() => resolve(queueRef.current.shift()))
    })
  }, [])

  // Connect proactively on mount or when session/mode changes
  // Mode change requires reconnect with force_new to restart Claude with new --permission-mode
  useEffect(() => {
    connect(currentSessionId, mode).catch(() => {
      // Connection failed, will retry on message send
    })
  }, [connect, currentSessionId, mode])

  const switchSession = useCallback((sessionId) => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    connect(sessionId).catch(() => {})
  }, [connect])

  // Force restart session (e.g., after permission change)
  const restartSession = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    // Reconnect with force_new to restart CLI with new settings
    const wsUrl = buildWsUrl(currentSessionId, modeRef.current, true) // force_new=true
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    ws.onopen = () => setIsConnected(true)
    ws.onclose = () => setIsConnected(false)
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.type === 'system' && payload.subtype === 'connected') {
          console.log('[ClaudeStream] Session restarted with new permissions')
        }
        queueRef.current?.push(payload)
        const waiter = waitersRef.current?.shift()
        if (waiter) waiter()
      } catch {}
    }
    return ws
  }, [currentSessionId])

  // Send approval decision through WebSocket
  // For control_response: decision is "allow" or "deny", toolInput is the original tool input
  const sendApprovalResponse = useCallback((decision, requestId, toolInput = {}, updatedInput, permissionSuggestions, message) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('[ClaudeStream] Cannot send approval - WebSocket not connected')
      return
    }
    const response = {
      type: 'control_response',
      request_id: requestId,
      decision,
      tool_input: toolInput,
    }
    if (updatedInput) {
      response.updatedInput = updatedInput
    }
    if (permissionSuggestions) {
      response.permission_suggestions = permissionSuggestions
    }
    if (message) {
      response.message = message
    }

    console.log('[ClaudeStream] Sending control response:', response)
    wsRef.current.send(JSON.stringify(response))
  }, [])

  // Send a message directly (for retry)
  const sendMessage = useCallback(async (text, files = []) => {
    if (!text?.trim()) return

    const ws = await connect(currentSessionId)
    ws.send(JSON.stringify({
      type: 'user',
      message: { role: 'user', content: [{ type: 'text', text }] },
      mode: modeRef.current,
      context_files: files,
    }))
  }, [connect, currentSessionId])

  const adapter = {
    async *run({ messages, abortSignal }) {
      const lastUser = messages.filter((m) => m.role === 'user').pop()
      const userText = lastUser?.content?.find((c) => c.type === 'text')?.text || ''
      const extracted = extractImagesFromText(userText, imageCacheRef.current)
      const cleanedText = extracted.text || ''
      const imageParts = extracted.images
        .map((img) => dataUrlToImagePart(img))
        .filter(Boolean)
      if (!cleanedText.trim() && imageParts.length === 0) return

      // Track last user message for potential retry
      const files = contextFilesRef.current.map(f => f.path)
      onLastMessageChange?.({ text: cleanedText, files })

      onStreamingChange?.(true)

      const ws = await connect(currentSessionId)
      queueRef.current = []
      waitersRef.current = []

      // Check if it's a slash command
      const trimmed = cleanedText.trim()
      if (trimmed.startsWith('/')) {
        const cmd = trimmed.split(' ')[0].toLowerCase()

        // Handle frontend commands locally
        if (cmd === '/clear') {
          yield { content: [{ type: 'text', text: 'Chat cleared.' }] }
          return
        }

        if (cmd === '/terminal') {
          yield { content: [{ type: 'text', text: 'Use the Terminal panel to access CLI mode.' }] }
          return
        }

        // Pass slash commands to CLI as regular user messages (per VSCode extension)
        // CLI interprets messages starting with / as commands
        ws.send(JSON.stringify({
          type: 'user',
          message: { role: 'user', content: [{ type: 'text', text: trimmed }] },
          mode: modeRef.current,
        }))
      } else {
        const content = []
        if (cleanedText.trim()) {
          content.push({ type: 'text', text: cleanedText })
        }
        content.push(...imageParts)
        ws.send(JSON.stringify({
          type: 'user',
          message: { role: 'user', content },
          mode: modeRef.current,
          context_files: files,
        }))
      }
      clearContextFilesRef.current?.()

      const parts = []
      let textPartIndex = -1
      const toolIndex = new Map()
      const toolSignature = new Set()
      const seenUuids = new Set() // Track seen message uuids to avoid duplicates
      let latestCommandOutput = null // Track latest command output (for slash commands, show only the last)
      let running = true

      while (running) {
        if (abortSignal?.aborted) break
        const payload = await nextPayload()
        if (!payload) continue

        // Log ALL incoming messages
        console.log('[ClaudeStream] <<', payload.type, payload.subtype || '', payload.uuid?.slice(0, 8) || '')

        if (payload.type === 'assistant') {
          const content = payload.message?.content || []
          content.forEach((part) => {
            if (part.type === 'text') {
              if (textPartIndex === -1) {
                parts.push({ type: 'text', text: part.text || '' })
                textPartIndex = parts.length - 1
              } else {
                const existing = parts[textPartIndex]
                existing.text = mergeStreamText(existing.text || '', part.text || '')
              }
            }
            if (part.type === 'tool_use') {
              // Skip if we already have this exact tool by ID
              if (toolIndex.has(part.id)) {
                return
              }
              // Create a signature based on tool name + key input params to avoid duplicates
              const inputKey = part.input?.file_path || part.input?.path || part.input?.command || part.id
              const signature = `${part.name}-${inputKey}`
              if (toolSignature.has(signature)) {
                // Update existing tool with this ID reference
                return
              }
              const toolPart = {
                type: 'tool_use',
                id: part.id,
                name: part.name,
                input: part.input || {},
                output: '',
                status: 'running',
                lineCount: null,
              }
              toolSignature.add(signature)
              toolIndex.set(part.id, toolPart)
              parts.push(toolPart)
              textPartIndex = -1
            }
          })
        }

        if (payload.type === 'user') {
          const messageUuid = payload.uuid || ''

          // Skip duplicates by uuid
          if (messageUuid && seenUuids.has(messageUuid)) {
            console.log('[ClaudeStream] Skip duplicate uuid:', messageUuid.slice(0, 8))
            continue
          }
          if (messageUuid) seenUuids.add(messageUuid)

          // Check for slash command output (wrapped in <local-command-stdout> tags)
          const messageContent = payload.message?.content
          if (typeof messageContent === 'string' && messageContent.includes('<local-command-stdout>')) {
            const match = messageContent.match(/<local-command-stdout>([\s\S]*?)<\/local-command-stdout>/)
            if (match) {
              // Store latest - we'll display only the last one when result arrives
              latestCommandOutput = match[1].trim()
              console.log('[ClaudeStream] Stored cmd output:', latestCommandOutput.slice(0, 50))
            }
          }

          const toolResult = payload.message?.content?.find?.((c) => c.type === 'tool_result')
          if (toolResult?.tool_use_id && toolIndex.has(toolResult.tool_use_id)) {
            const toolPart = toolIndex.get(toolResult.tool_use_id)
            const resultText = [
              toolResult.content,
              payload.tool_use_result?.stdout,
              payload.tool_use_result?.stderr,
            ]
              .filter(Boolean)
              .join('\n')
            if ((toolPart.name || '').toLowerCase() === 'read') {
              const lines = resultText ? resultText.split('\n').length : 0
              toolPart.lineCount = lines
              toolPart.output = ''
            } else {
              toolPart.output = mergeStreamText(toolPart.output || '', resultText)
            }
            toolPart.status = toolResult.is_error ? 'error' : 'complete'
          }
        }

        // Handle control_request from CLI (interactive permission prompt)
        // This is sent when --permission-prompt-tool stdio is used
        if (payload.type === 'control_request') {
          console.log('[ClaudeStream] Control request detected:', payload)
          onStreamingChange?.({
            type: 'control_request',
            payload,
          })
        }
        if (payload.type === 'control_cancel_request') {
          console.log('[ClaudeStream] Control cancel detected:', payload)
          onStreamingChange?.({
            type: 'control_cancel_request',
            payload,
          })
        }

        // Also check for explicit permission request messages (if Claude sends them)
        const isPermissionRequest =
          payload.type === 'permission_request' ||
          payload.type === 'approval_request' ||
          payload.type === 'input_request' ||
          payload.type === 'user_input_request' ||
          (payload.type === 'system' && payload.subtype === 'permission_request')

        if (isPermissionRequest) {
          console.log('[ClaudeStream] Permission request detected:', payload)
          onStreamingChange?.({
            type: 'permission',
            payload,
          })
        }

        if (payload.type === 'result') {
          running = false

          // Add the latest command output (if any) now that we have the final result
          if (latestCommandOutput) {
            console.log('[ClaudeStream] Adding final output:', latestCommandOutput.slice(0, 50))
            parts.push({ type: 'text', text: latestCommandOutput })
            textPartIndex = parts.length - 1
          }

          // Check for permission denials BEFORE signaling end
          // In --print mode, Claude reports denied tools in the result
          if (payload.permission_denials?.length > 0) {
            console.log('[ClaudeStream] Permission denials found:', JSON.stringify(payload.permission_denials, null, 2))
            // Show the first denied tool for user to grant permission
            const denial = payload.permission_denials[0]
            onStreamingChange?.({
              type: 'permission_denied',
              payload: {
                tool_name: denial.tool_name,
                tool_use_id: denial.tool_use_id,
                tool_input: denial.tool_input,
              },
            })
            // Don't call onStreamingChange(false) - keep showing the panel
          } else {
            // No denials, signal end of streaming
            onStreamingChange?.(false)
          }
        }

        yield { content: parts.map((part) => ({ ...part })) }
      }
    },
  }

  return { adapter, sessionName, isConnected, switchSession, sendApprovalResponse, sendMessage, restartSession }
}

const renderToolPart = (part) => {
  const input = part.input || {}
  const output = part.output || ''
  const toolName = (part.name || '').toLowerCase()

  if (toolName === 'bash') {
    return (
      <BashToolRenderer
        command={input.command || input.cmd}
        description={input.description}
        output={output}
        status={part.status}
        compact={true}
      />
    )
  }
  if (toolName === 'read') {
    return (
      <ReadToolRenderer
        filePath={input.path || input.file_path}
        content={null}
        lineCount={part.lineCount || undefined}
        status={part.status}
        hideContent={true}
      />
    )
  }
  if (toolName === 'write') {
    return (
      <WriteToolRenderer
        filePath={input.path || input.file_path}
        content={input.content || output}
        status={part.status}
      />
    )
  }
  if (toolName === 'edit') {
    return (
      <EditToolRenderer
        filePath={input.path || input.file_path}
        diff={input.diff || output}
        status={part.status}
      />
    )
  }
  if (toolName === 'glob') {
    return (
      <GlobToolRenderer
        pattern={input.pattern || input.glob}
        files={parseGlobFiles(output)}
        status={part.status}
      />
    )
  }
  if (toolName === 'grep') {
    return (
      <GrepToolRenderer
        pattern={input.pattern || input.query}
        path={input.path}
        results={parseGrepResults(output)}
        status={part.status}
      />
    )
  }

  return <ToolFallback name={part.name} input={input} output={output} />
}

const AssistantMessage = () => {
  const message = useMessage()
  const content = message.content || []
  const isStreaming = message.status?.type === 'running'

  return (
    <MessagePrimitive.Root
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--chat-spacing-sm, 8px)',
      }}
    >
      {content.map((part, index) => {
        if (part.type === 'text') {
          return (
            <div key={`text-${index}`} className="claude-assistant-line">
              <span
                className="claude-assistant-bullet"
                style={{ color: isStreaming ? '#ae5630' : '#858585' }}
              >
                ●
              </span>
              <div className="claude-assistant-text">
                <TextBlock text={part.text} />
                {isStreaming && (
                  <span
                    style={{
                      display: 'inline-block',
                      width: '2px',
                      height: '16px',
                      backgroundColor: '#cccccc',
                      marginLeft: '2px',
                      animation: 'blink 1s step-end infinite',
                    }}
                  />
                )}
              </div>
            </div>
          )
        }

        if (part.type === 'tool_use') {
          return (
            <div key={`tool-${part.id || index}`}>
              {renderToolPart(part)}
            </div>
          )
        }
        return null
      })}
    </MessagePrimitive.Root>
  )
}

const MODES = [
  { id: 'ask', title: 'Ask', description: 'Asks for approval for each action.' },
  { id: 'act', title: 'Auto-Accept', description: 'Automatically accepts file edits.' },
  { id: 'plan', title: 'Plan', description: 'Defines a plan before acting.' },
]

const ImageIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
    <rect x="3" y="5" width="18" height="14" rx="2" ry="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
    <circle cx="8" cy="10" r="1.5" fill="currentColor" />
    <path d="M21 16l-5-5-4 4-2-2-5 5" fill="none" stroke="currentColor" strokeWidth="1.5" />
  </svg>
)

const INLINE_IMAGE_LIMIT = 80000

const ComposerShell = ({
  isConnected,
  mode,
  setMode,
  showModeMenu,
  setShowModeMenu,
  attachments,
  setAttachments,
  contextFiles,
  setContextFiles,
  onRegisterImages,
}) => {
  const composer = useComposer()
  const api = useAssistantApi()
  const thread = useThread()
  const isRunning = thread.isRunning
  const [showSlashMenu, setShowSlashMenu] = useState(false)
  const [showAtMenu, setShowAtMenu] = useState(false)
  const [menuFilter, setMenuFilter] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [menuNavigated, setMenuNavigated] = useState(false)
  const currentMode = MODES.find((item) => item.id === mode) || MODES[0]
  const modeLabel = currentMode?.title || mode
  const modeIcon = (modeLabel || 'M').charAt(0).toUpperCase()

  const inputRef = useRef(null)

  const applyComposerText = useCallback((nextText) => {
    composer?.setText?.(nextText)
    if (inputRef.current) {
      const nativeSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        'value'
      )?.set
      if (nativeSetter) {
        nativeSetter.call(inputRef.current, nextText)
        inputRef.current.dispatchEvent(new Event('input', { bubbles: true }))
      }
    }
  }, [composer])

  const appendAttachmentsToText = useCallback(() => {
    if (attachments.length === 0) return
    const currentText = composer?.text || ''
    const hasImage = attachments.some((img) => currentText.includes(img.dataUrl))
    if (hasImage) return
    const markdown = attachments
      .map((img, idx) => {
        const token = `[[image:${img.id}]]`
        if (img.dataUrl && img.dataUrl.length <= INLINE_IMAGE_LIMIT) {
          return `![pasted-image-${idx + 1}](${img.dataUrl})`
        }
        onRegisterImages?.(img)
        return token
      })
      .join('\n')
    const nextText = currentText.trim()
      ? `${currentText.trimEnd()}\n\n${markdown}`
      : markdown
    applyComposerText(nextText)
    setAttachments([])
  }, [attachments, composer, setAttachments, applyComposerText, onRegisterImages])
  const slashMenuRef = useRef(null)

  // Close slash menu when clicking outside
  useEffect(() => {
    if (!showSlashMenu && !showAtMenu) return
    const handleClickOutside = (event) => {
      if (slashMenuRef.current && !slashMenuRef.current.contains(event.target)) {
        setShowSlashMenu(false)
        setShowAtMenu(false)
        setMenuNavigated(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showSlashMenu, showAtMenu])


  const [searchedFiles, setSearchedFiles] = useState([])

  const filteredCommands = SLASH_COMMANDS.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(menuFilter.toLowerCase()) ||
      cmd.description.toLowerCase().includes(menuFilter.toLowerCase())
  )

  // Fetch files when @ menu filter changes
  useEffect(() => {
    if (!showAtMenu) return
    const query = menuFilter || ''
    if (query.length < 1) {
      setSearchedFiles([])
      return
    }
    const controller = new AbortController()
    searchFiles(query).then((files) => {
      if (!controller.signal.aborted) {
        setSearchedFiles(files.slice(0, 10))
      }
    })
    return () => controller.abort()
  }, [showAtMenu, menuFilter])

  const handleMenuSelect = (item, type) => {
    if (type === 'at') {
      // Add file to context (if not already added)
      setContextFiles?.((prev) => {
        if (prev.some((f) => f.id === item.id)) return prev
        return [...prev, item]
      })
      // Clear the @ from input
      const currentText = composer?.text || ''
      const atIndex = currentText.lastIndexOf('@')
      if (atIndex >= 0) {
        const newText = currentText.slice(0, atIndex).trimEnd()
        applyComposerText(newText)
      }
    } else {
      // Slash command - insert text
      const newValue = `${item.label} `
      applyComposerText(newValue)
    }
    composer?.focus?.()
    setShowSlashMenu(false)
    setShowAtMenu(false)
  }

  const handleKeyDown = (event) => {
    if (showSlashMenu || showAtMenu) {
      const list = showAtMenu ? searchedFiles : filteredCommands
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setSelectedIndex((prev) => Math.min(prev + 1, list.length - 1))
        setMenuNavigated(true)
        return
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault()
        setSelectedIndex((prev) => Math.max(prev - 1, 0))
        setMenuNavigated(true)
        return
      }
      if (event.key === 'Enter') {
        event.preventDefault()
        if (list.length > 0) {
          const index = menuNavigated ? selectedIndex : 0
          handleMenuSelect(list[index], showAtMenu ? 'at' : 'slash')
          setMenuNavigated(false)
          return
        }
        setShowSlashMenu(false)
        setShowAtMenu(false)
        return
      }
      if (event.key === 'Escape') {
        event.preventDefault()
        setShowSlashMenu(false)
        setShowAtMenu(false)
        setMenuNavigated(false)
      }
    }

    if (event.key === 'Enter' && !event.shiftKey && !showSlashMenu && !showAtMenu) {
      if (attachments.length > 0) {
        event.preventDefault()
        appendAttachmentsToText()
        requestAnimationFrame(() => api.composer().send())
        return
      }
      appendAttachmentsToText()
    }
  }

  const handlePaste = (event) => {
    const items = Array.from(event.clipboardData?.items || [])
    const imageItems = items.filter((item) => item.type.startsWith('image/'))
    if (imageItems.length === 0) return

    event.preventDefault()
    imageItems.forEach((item) => {
      const file = item.getAsFile()
      if (!file) return
      const reader = new FileReader()
      reader.onload = () => {
        setAttachments((prev) => [
          ...prev,
          { id: `${Date.now()}-${file.name}`, dataUrl: reader.result, name: file.name },
        ])
      }
      reader.readAsDataURL(file)
    })
  }

  return (
    <ComposerPrimitive.Root className="claude-input">
      <div className="claude-input-box" ref={slashMenuRef}>
        {(showSlashMenu || showAtMenu) && (
          <div className="claude-menu">
            {showSlashMenu &&
              filteredCommands.map((cmd, idx) => (
                <button
                  key={cmd.id}
                  className={`claude-menu-item ${idx === selectedIndex ? 'selected' : ''}`}
                  onPointerDown={(event) => {
                    event.preventDefault()
                    event.stopPropagation()
                    handleMenuSelect(cmd, 'slash')
                  }}
                  type="button"
                >
                  <span>{cmd.label}</span>
                  <span className="desc">{cmd.description}</span>
                </button>
              ))}
            {showAtMenu &&
              searchedFiles.map((file, idx) => (
                <button
                  key={file.id}
                  className={`claude-menu-item ${idx === selectedIndex ? 'selected' : ''}`}
                  onPointerDown={(event) => {
                    event.preventDefault()
                    event.stopPropagation()
                    handleMenuSelect(file, 'at')
                  }}
                  type="button"
                >
                  <span>@{file.label}</span>
                  <span className="desc">{file.path}</span>
                </button>
              ))}
          </div>
        )}
        {attachments.length > 0 && (
          <div className="claude-attachments">
            {attachments.map((img) => (
              <div key={img.id} className="claude-attachment">
                <img src={img.dataUrl} alt={img.name} />
                <button
                  type="button"
                  onClick={() => setAttachments((prev) => prev.filter((item) => item.id !== img.id))}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
        {contextFiles?.length > 0 && (
          <div className="claude-context-files">
            {contextFiles.map((file) => (
              <div key={file.id} className="claude-context-pill">
                <span className="claude-context-pill-icon">📄</span>
                <span className="claude-context-pill-label">{file.label}</span>
                <button
                  type="button"
                  onClick={() => setContextFiles?.((prev) => prev.filter((f) => f.id !== file.id))}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
        <ComposerPrimitive.Input
          ref={inputRef}
          autoFocus
          placeholder={isConnected ? 'Reply...' : 'Connecting...'}
          rows={1}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          onChange={(e) => {
            const text = e.target.value
            const lastChar = text.slice(-1)
            const prevChar = text.slice(-2, -1)
            if (lastChar === '/' && (prevChar === '' || prevChar === ' ')) {
              setShowSlashMenu(true)
              setShowAtMenu(false)
              setMenuFilter('')
              setSelectedIndex(0)
              setMenuNavigated(false)
            } else if (lastChar === '@' && (prevChar === '' || prevChar === ' ')) {
              setShowAtMenu(true)
              setShowSlashMenu(false)
              setMenuFilter('')
              setSelectedIndex(0)
              setMenuNavigated(false)
            } else if (showSlashMenu) {
              const triggerIndex = text.lastIndexOf('/')
              if (triggerIndex >= 0) {
                setMenuFilter(text.slice(triggerIndex + 1))
              } else {
                setShowSlashMenu(false)
                setMenuNavigated(false)
              }
            } else if (showAtMenu) {
              const triggerIndex = text.lastIndexOf('@')
              if (triggerIndex >= 0) {
                setMenuFilter(text.slice(triggerIndex + 1))
              } else {
                setShowAtMenu(false)
                setMenuNavigated(false)
              }
            }
          }}
        />
        <div className="claude-input-actions">
          <div className="claude-input-left">
            <label className="claude-icon-button" title="Attach image">
              <ImageIcon />
              <input
                type="file"
                accept="image/*"
                className="claude-file-input"
                multiple
                onChange={(event) => {
                  const files = Array.from(event.target.files || [])
                  files.forEach((file) => {
                    const reader = new FileReader()
                    reader.onload = () => {
                      setAttachments((prev) => [
                        ...prev,
                        { id: `${Date.now()}-${file.name}`, dataUrl: reader.result, name: file.name },
                      ])
                    }
                    reader.readAsDataURL(file)
                  })
                  event.target.value = ''
                }}
              />
            </label>
            <button
              type="button"
              className="claude-icon-button"
              title="Slash commands"
              onMouseDown={(event) => {
                event.preventDefault()
                event.stopPropagation()
                const currentText = composer?.text || ''
                if (!currentText.endsWith('/')) {
                  applyComposerText(`${currentText}/`)
                }
                setShowSlashMenu(true)
                setShowAtMenu(false)
                setSelectedIndex(0)
                setMenuFilter('')
                setMenuNavigated(false)
                setTimeout(() => composer?.focus?.(), 0)
              }}
            >
              /
            </button>
            <button
              type="button"
              className="claude-icon-button"
              title="Mention file"
              onMouseDown={(event) => {
                event.preventDefault()
                event.stopPropagation()
                const currentText = composer?.text || ''
                if (!currentText.endsWith('@')) {
                  applyComposerText(`${currentText}@`)
                }
                setShowAtMenu(true)
                setShowSlashMenu(false)
                setSelectedIndex(0)
                setMenuFilter('')
                setMenuNavigated(false)
                setTimeout(() => composer?.focus?.(), 0)
              }}
            >
              @
            </button>
          </div>
          <div className="claude-input-right">
            <div className="claude-mode-wrapper">
              <button
                type="button"
                className="claude-mode-button"
                onClick={() => setShowModeMenu((prev) => !prev)}
              >
                <span className={`claude-mode-icon claude-mode-${mode}`}>{modeIcon}</span>
                <span className="claude-mode-label">{modeLabel}</span>
              </button>
              {showModeMenu && (
                <div className="claude-mode-menu">
                  {MODES.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={`claude-mode-item ${mode === item.id ? 'active' : ''}`}
                      onClick={() => {
                        setMode(item.id)
                        setShowModeMenu(false)
                      }}
                    >
                      <span className={`claude-mode-icon claude-mode-${item.id}`}>
                        {item.title[0]}
                      </span>
                      <span className="claude-mode-text">
                        <span className="claude-mode-title">{item.title}</span>
                        <span className="claude-mode-desc">{item.description}</span>
                      </span>
                      {mode === item.id && <span className="claude-mode-check">v</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {isRunning ? (
              <ComposerPrimitive.Cancel className="claude-send claude-stop">
                ■
              </ComposerPrimitive.Cancel>
            ) : (
              <ComposerPrimitive.Send
                className="claude-send"
                disabled={!isConnected}
                onClick={() => appendAttachmentsToText()}
              >
                ↑
              </ComposerPrimitive.Send>
            )}
          </div>
        </div>
      </div>
    </ComposerPrimitive.Root>
  )
}

const extractMarkdownImages = (text, imageCache) => {
  if (!text) return { text, images: [] }
  const images = []
  let cleaned = text
  const regex = /!\[[^\]]*\]\(([^)]+)\)/g
  let match
  while ((match = regex.exec(text)) !== null) {
    images.push(match[1])
  }
  const tokenRegex = /\[\[image:([^\]]+)\]\]/g
  while ((match = tokenRegex.exec(text)) !== null) {
    const cached = imageCache?.[match[1]]
    if (cached) {
      images.push(cached.dataUrl || cached)
    }
  }
  cleaned = cleaned.replace(regex, '').replace(tokenRegex, '').trim()
  return { text: cleaned, images }
}

const UserMessageWithImages = ({ imageCache }) => {
  const message = useMessage()
  const rawText = message.content?.find((part) => part.type === 'text')?.text || ''
  const { text, images } = extractMarkdownImages(rawText, imageCache)

  return (
    <MessagePrimitive.Root
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        marginBottom: 'var(--chat-spacing-md, 12px)',
        gap: '8px',
      }}
    >
      {text && <div className="claude-user-bubble">{text}</div>}
      {images.length > 0 && (
        <div className="claude-user-attachments">
          {images.map((src, idx) => (
            <div key={`${src}-${idx}`} className="claude-user-attachment">
              <img src={src} alt={`attachment-${idx + 1}`} />
            </div>
          ))}
        </div>
      )}
    </MessagePrimitive.Root>
  )
}

const Thread = ({
  sessionName,
  isConnected,
  attachments,
  setAttachments,
  contextFiles,
  setContextFiles,
  sessions,
  showSessionDropdown,
  setShowSessionDropdown,
  onSelectSession,
  onNewSession,
  mode,
  setMode,
  approvalRequest,
  onApprovalDecision,
  imageCache,
  onRegisterImages,
}) => {
  const [showModeMenu, setShowModeMenu] = useState(false)
  const sessionDropdownRef = useRef(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!showSessionDropdown) return
    const handleClickOutside = (event) => {
      if (sessionDropdownRef.current && !sessionDropdownRef.current.contains(event.target)) {
        setShowSessionDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showSessionDropdown, setShowSessionDropdown])

  return (
    <ChatPanel>
      <div className="claude-stream-header">
        <div className="claude-stream-title">
          <span className="mark">✳</span>
          <span>Claude Code</span>
        </div>
        <div className="claude-stream-header-actions">
          <button type="button" title="Lock">🔒</button>
          <button type="button" title="More">⋯</button>
        </div>
      </div>

      <div style={{ position: 'relative' }} ref={sessionDropdownRef}>
        <SessionHeader
          title={sessionName}
          onTitleClick={() => setShowSessionDropdown((prev) => !prev)}
          onNewSession={onNewSession}
        />
        {showSessionDropdown && (
          <div className="claude-session-dropdown">
            {sessions.length === 0 ? (
              <div className="claude-session-item empty">No other sessions</div>
            ) : (
              sessions.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className={`claude-session-item ${s.id === sessionName ? 'active' : ''}`}
                  onClick={() => {
                    onSelectSession(s.id)
                    setShowSessionDropdown(false)
                  }}
                >
                  <span className="claude-session-id">{s.id.slice(0, 8)}...</span>
                  <span className="claude-session-meta">
                    {s.clients} client{s.clients !== 1 ? 's' : ''}
                  </span>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <MessageList>
        <EmptyState>
          <div className="claude-stream-empty">
            <span className="mark">✳</span>
            <div className="headline">Claude Code</div>
            <div className="hint">Type /model to pick the right tool for the job.</div>
          </div>
        </EmptyState>
        <Messages
          components={{
            UserMessage: () => <UserMessageWithImages imageCache={imageCache} />,
            AssistantMessage,
          }}
        />
      </MessageList>

      <AssistantIf condition={({ thread }) => thread.isRunning}>
        <div className="claude-status">
          <span className="mark">✳</span>
          <span style={{ fontStyle: 'italic' }}>Brewing...</span>
        </div>
      </AssistantIf>
      {approvalRequest && (
        <div className="claude-permission-panel">
          <PermissionPanel
            title={approvalRequest.title}
            options={approvalRequest.options}
            diff={approvalRequest.diff}
            filePath={approvalRequest.file_path}
            toolName={approvalRequest.tool_name}
            toolInput={approvalRequest.tool_input}
            blockedPath={approvalRequest.blocked_path}
            permissionSuggestions={approvalRequest.permission_suggestions}
            onSelect={onApprovalDecision}
          />
        </div>
      )}
      <ComposerShell
        isConnected={isConnected}
        mode={mode}
        setMode={setMode}
        showModeMenu={showModeMenu}
        setShowModeMenu={setShowModeMenu}
        attachments={attachments}
        setAttachments={setAttachments}
        contextFiles={contextFiles}
        setContextFiles={setContextFiles}
        onRegisterImages={onRegisterImages}
      />
    </ChatPanel>
  )
}

export default function ClaudeStreamChat({ initialSessionId = null, provider = 'claude' }) {
  const [attachments, setAttachments] = useState([])
  const [contextFiles, setContextFiles] = useState([])
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(initialSessionId)
  const [showSessionDropdown, setShowSessionDropdown] = useState(false)
  const [mode, setMode] = useState('ask')
  const [approvalRequest, setApprovalRequest] = useState(null)
  const [imageCache, setImageCache] = useState({})
  const [lastUserMessage, setLastUserMessage] = useState(null)
  const retryMessageRef = useRef(null)

  // Update session ID when initialSessionId prop changes
  useEffect(() => {
    if (initialSessionId && initialSessionId !== currentSessionId) {
      setCurrentSessionId(initialSessionId)
    }
  }, [initialSessionId])

  // Fetch sessions on mount and when dropdown opens
  useEffect(() => {
    if (showSessionDropdown) {
      fetchSessions().then(setSessions)
    }
  }, [showSessionDropdown])

  // Note: Approval polling removed - using native stream-json permission messages instead
  // The hook-based approach can be re-enabled by uncommenting and configuring .claude/settings.json hooks

  const clearContextFiles = useCallback(() => setContextFiles([]), [])
  const sendApprovalResponseRef = useRef(null)
  const handleStreamingChange = useCallback((event) => {
    // Handle boolean (start/stop streaming)
    if (typeof event === 'boolean') {
      if (!event) {
        // Clear any pending approval when stream ends
        setApprovalRequest(null)
      }
      return
    }

    // Handle permission denial from result (--print mode)
    // Claude reports what was blocked (informational only)
    if (event?.type === 'permission_denied') {
      const payload = event.payload
      const tool = payload.tool_name || 'tool'
      const toolInput = payload.tool_input || {}
      const blockedPath = payload.blocked_path || payload.blockedPath || ''
      const filePath = toolInput.file_path || toolInput.path || toolInput.command || blockedPath || ''

      setApprovalRequest({
        id: payload.tool_use_id || `denied-${Date.now()}`,
        title: `${tool} was blocked`,
        tool_name: tool,
        tool_input: toolInput,
        file_path: filePath,
        source: 'denial',
        options: [
          { label: 'Dismiss', decision: 'dismiss' },
        ],
      })
      return
    }

    // Handle control_request from CLI (interactive permission prompt)
    // This is the native permission flow when using --permission-prompt-tool stdio
    if (event?.type === 'control_request') {
      const payload = event.payload
      const request = payload.request || {}
      const toolName = request.tool_name || request.toolName || 'tool'
      const toolInput = request.input || request.tool_input || request.inputs || {}
      const permissionSuggestions = request.permission_suggestions || request.suggestions || []
      const blockedPath = request.blocked_path || request.blockedPath || ''
      const filePath = toolInput.file_path || toolInput.path || toolInput.command || ''

      setApprovalRequest({
        id: payload.request_id || `control-${Date.now()}`,
        tool_name: toolName,
        tool_input: toolInput,
        file_path: filePath,
        blocked_path: blockedPath,
        permission_suggestions: permissionSuggestions,
        source: 'control_request',  // Mark as control request for proper response format
      })
      return
    }
    if (event?.type === 'control_cancel_request') {
      const requestId = event.payload?.request_id
      if (!requestId) {
        setApprovalRequest(null)
        return
      }
      setApprovalRequest((current) => (current && current.id === requestId ? null : current))
      return
    }

    // Handle explicit permission request from stream
    if (event?.type === 'permission') {
      const payload = event.payload
      const tool = payload.tool_name || payload.tool || payload.name || 'tool'
      const filePath = payload.file_path || payload.path || ''
      const diff = payload.diff || ''
      const toolInput = payload.tool_input || payload.input || {}
      setApprovalRequest({
        id: payload.id || payload.tool_use_id || `stream-${Date.now()}`,
        diff,
        tool_name: tool,
        tool_input: toolInput,
        file_path: filePath,
        source: 'stream',
      })
    }
  }, [])

  const handleLastMessageChange = useCallback((msg) => {
    setLastUserMessage(msg)
    retryMessageRef.current = msg
  }, [])

  const { adapter, sessionName, isConnected, switchSession, sendApprovalResponse, sendMessage, restartSession } = useClaudeStreamRuntime(
    currentSessionId,
    setCurrentSessionId,
    mode,
    contextFiles,
    clearContextFiles,
    handleStreamingChange,
    handleLastMessageChange,
    imageCache
  )
  const runtime = useLocalRuntime(adapter)

  // Store sendApprovalResponse in ref for use in callback
  useEffect(() => {
    sendApprovalResponseRef.current = sendApprovalResponse
  }, [sendApprovalResponse])

  const handleApprovalDecision = useCallback(async (option) => {
    if (!option || !approvalRequest?.id) {
      setApprovalRequest(null)
      return
    }

    const decision = option.decision || (option.label?.toLowerCase().includes('deny') ? 'deny' : 'allow')
    if (decision === 'dismiss') {
      setApprovalRequest(null)
      return
    }

    if (approvalRequest.source === 'control_request' && sendApprovalResponseRef.current) {
      // Send control_response for control_request (native permission flow)
      // Must include tool_input for CLI to execute the tool
      sendApprovalResponseRef.current(
        decision,
        approvalRequest.id,
        approvalRequest.tool_input || {},
        option.updatedInput,
        option.permissionSuggestions,
        option.message
      )
    } else if (approvalRequest.source === 'stream' && sendApprovalResponseRef.current) {
      // Send through WebSocket for stream-based permissions (legacy)
      sendApprovalResponseRef.current(
        decision,
        approvalRequest.id,
        approvalRequest.tool_input || {},
        option.updatedInput,
        option.permissionSuggestions,
        option.message
      )
    }

    if (option.nextMode && option.nextMode !== mode) {
      setMode(option.nextMode)
    }
    setApprovalRequest(null)
  }, [approvalRequest, mode])

  const handleNewSession = useCallback(async () => {
    const newId = await createNewSession()
    if (newId) {
      switchSession(newId)
      // Refresh sessions list
      fetchSessions().then(setSessions)
    }
  }, [switchSession])

  const handleSelectSession = useCallback((sessionId) => {
    switchSession(sessionId)
  }, [switchSession])
  const handleRegisterImages = useCallback((image) => {
    if (!image?.id) return
    setImageCache((prev) => ({ ...prev, [image.id]: image }))
  }, [])

  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden' }}>
      <style>{chatThemeVars}</style>
      <style>{assistantMessageStyles}</style>
      <AssistantRuntimeProvider runtime={runtime}>
        <Thread
          sessionName={sessionName}
          isConnected={isConnected}
          attachments={attachments}
          setAttachments={setAttachments}
          contextFiles={contextFiles}
          setContextFiles={setContextFiles}
          sessions={sessions}
          showSessionDropdown={showSessionDropdown}
          setShowSessionDropdown={setShowSessionDropdown}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          mode={mode}
          setMode={setMode}
          approvalRequest={approvalRequest}
          onApprovalDecision={handleApprovalDecision}
          imageCache={imageCache}
          onRegisterImages={handleRegisterImages}
        />
      </AssistantRuntimeProvider>
    </div>
  )
}
