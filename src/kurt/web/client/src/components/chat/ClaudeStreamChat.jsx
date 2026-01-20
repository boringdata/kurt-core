import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Image, FileText, Loader2, Sparkles, RotateCcw, RefreshCw, Settings, MoreHorizontal } from 'lucide-react'
import {
  AssistantIf,
  AssistantRuntimeProvider,
  useLocalRuntime,
  MessagePrimitive,
  ComposerPrimitive,
  useAssistantApi,
  useMessage,
  useAssistantState,
} from '@assistant-ui/react'
import ChatPanel, { chatThemeVars } from './ChatPanel'
import MessageList, { Messages, EmptyState } from './MessageList'
import TextBlock from './TextBlock'
import SessionHeader from './SessionHeader'
import BashToolRenderer from './BashToolRenderer'
import ReadToolRenderer from './ReadToolRenderer'
import WriteToolRenderer from './WriteToolRenderer'
import EditToolRenderer from './EditToolRenderer'
import GlobToolRenderer from './GlobToolRenderer'
import GrepToolRenderer from './GrepToolRenderer'
import ToolUseBlock, { ToolOutput } from './ToolUseBlock'
import PermissionPanel from './PermissionPanel'
import './styles.css'

// Helper to safely find content in arrays (content might be a string sometimes)
const findContent = (content, predicate) => {
  if (!Array.isArray(content)) return undefined
  return content.find(predicate)
}

const extractResultText = (payload) => {
  const raw = payload?.result
  if (!raw) return ''
  if (typeof raw === 'string') return raw
  if (typeof raw?.text === 'string') return raw.text
  if (typeof raw?.message === 'string') return raw.message
  if (typeof raw?.result === 'string') return raw.result
  const content = raw?.content
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    const textPart = content.find((part) => part?.type === 'text')
    if (textPart?.text) return textPart.text
  }
  return ''
}

const DEFAULT_SLASH_COMMANDS = [
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

const HISTORY_STORAGE_PREFIX = 'kurt-web-claude-stream-history'
const HISTORY_LIMIT = 200

const getHistoryKey = (sessionId) => {
  if (!sessionId) return null
  return `${HISTORY_STORAGE_PREFIX}-${sessionId}`
}

const loadStoredHistory = (sessionId) => {
  const key = getHistoryKey(sessionId)
  if (!key) return []
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
  } catch {
    return []
  }
}

const saveStoredHistory = (sessionId, messages) => {
  const key = getHistoryKey(sessionId)
  if (!key) return
  try {
    localStorage.setItem(key, JSON.stringify(messages))
  } catch {
    // Ignore storage errors
  }
}

const normalizeSlashCommands = (commands) => {
  if (!Array.isArray(commands)) return DEFAULT_SLASH_COMMANDS
  const seen = new Set()
  const normalized = commands
    .map((name) => String(name || '').trim())
    .filter(Boolean)
    .filter((name) => {
      if (seen.has(name)) return false
      seen.add(name)
      return true
    })
    .map((name) => ({
      id: name,
      label: name.startsWith('/') ? name : `/${name}`,
      description: 'Command',
    }))
  return normalized.length ? normalized : DEFAULT_SLASH_COMMANDS
}

const CLI_OPTIONS_KEY = 'kurt-web-claude-cli-options'
const DEFAULT_CLI_OPTIONS = {
  model: '',
  maxThinkingTokens: '',
  maxTurns: '',
  maxBudgetUsd: '',
  allowedTools: '',
  disallowedTools: '',
}

const buildRestartKey = (options) => {
  const normalized = {
    maxTurns: String(options?.maxTurns || '').trim(),
    maxBudgetUsd: String(options?.maxBudgetUsd || '').trim(),
    allowedTools: options?.allowedTools?.trim() || '',
    disallowedTools: options?.disallowedTools?.trim() || '',
  }
  return JSON.stringify(normalized)
}

const formatSessionLabel = (sessionId, sessions) => {
  if (!sessionId) return 'New conversation'
  const shortId = sessionId.slice(0, 8)
  const index = sessions.findIndex((session) => session.id === sessionId)
  const prefix = index >= 0 ? `Session ${index + 1} (Claude)` : 'Session (Claude)'
  return `${prefix} - ${shortId}`
}

const normalizeStoredOptions = (options) => ({
  model: options?.model?.trim() || '',
  maxThinkingTokens: String(options?.maxThinkingTokens || '').trim(),
  maxTurns: String(options?.maxTurns || '').trim(),
  maxBudgetUsd: String(options?.maxBudgetUsd || '').trim(),
  allowedTools: options?.allowedTools?.trim() || '',
  disallowedTools: options?.disallowedTools?.trim() || '',
})

const buildFileSpec = (attachment) => {
  if (!attachment?.fileId || !attachment?.relativePath) return ''
  return `${attachment.fileId}:${attachment.relativePath}`
}

const getApiBase = () => {
  const apiUrl = import.meta.env.VITE_API_URL || ''
  return apiUrl ? apiUrl.replace(/\/$/, '') : ''
}

const buildWsUrl = (
  sessionId,
  mode,
  forceNew = false,
  resume = false,
  options = {},
  fileSpecs = []
) => {
  const apiUrl = import.meta.env.VITE_API_URL || ''
  const queryParams = new URLSearchParams()
  if (sessionId) queryParams.set('session_id', sessionId)
  if (mode) queryParams.set('mode', mode)
  if (forceNew) queryParams.set('force_new', '1')
  if (resume) queryParams.set('resume', '1')
  if (options?.model) queryParams.set('model', options.model)
  if (options?.maxThinkingTokens) queryParams.set('max_thinking_tokens', options.maxThinkingTokens)
  if (options?.maxTurns) queryParams.set('max_turns', options.maxTurns)
  if (options?.maxBudgetUsd) queryParams.set('max_budget_usd', options.maxBudgetUsd)
  if (options?.allowedTools) queryParams.set('allowed_tools', options.allowedTools)
  if (options?.disallowedTools) queryParams.set('disallowed_tools', options.disallowedTools)
  if (Array.isArray(fileSpecs)) {
    fileSpecs.forEach((spec) => {
      if (spec) queryParams.append('file', spec)
    })
  }
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

const uploadAttachment = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${getApiBase()}/api/attachments`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    throw new Error('Upload failed')
  }
  return res.json()
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

const searchFiles = async (query, onError) => {
  if (!query || query.length < 1) return []
  try {
    const res = await fetch(`${getApiBase()}/api/search?q=${encodeURIComponent(query)}`)
    if (!res.ok) {
      onError?.({
        title: 'File search failed',
        detail: 'The backend returned an error while searching files.',
        suggestions: ['Check the backend status and retry.'],
        source: 'search',
        canRetry: true,
        canRestart: false,
      }, { showBanner: false })
      return []
    }
    const data = await res.json()
    return (data.results || []).map((f) => ({
      id: f.path,
      label: f.name,
      path: f.path,
      dir: f.dir,
    }))
  } catch (error) {
    onError?.({
      title: 'File search failed',
      detail: error?.message || 'Unable to reach the backend.',
      suggestions: ['Check the backend status and retry.'],
      source: 'search',
      canRetry: true,
      canRestart: false,
    }, { showBanner: false })
    return []
  }
}

const fetchMentionDefaults = async (onError) => {
  try {
    const res = await fetch(`${getApiBase()}/api/tree?path=.`)
    if (!res.ok) {
      onError?.({
        title: 'File list failed',
        detail: 'The backend returned an error while listing files.',
        suggestions: ['Check the backend status and retry.'],
        source: 'search',
        canRetry: true,
        canRestart: false,
      }, { showBanner: false })
      return []
    }
    const data = await res.json()
    const entries = Array.isArray(data.entries) ? data.entries : []
    const files = entries.filter((entry) => !entry.is_dir)
    return files.map((file) => ({
      id: file.path,
      label: file.name,
      path: file.path,
      dir: file.path.includes('/') ? file.path.split('/').slice(0, -1).join('/') : '',
    }))
  } catch (error) {
    onError?.({
      title: 'File list failed',
      detail: error?.message || 'Unable to reach the backend.',
      suggestions: ['Check the backend status and retry.'],
      source: 'search',
      canRetry: true,
      canRestart: false,
    }, { showBanner: false })
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
  cliOptions,
  resume,
  contextFiles,
  clearContextFiles,
  fileAttachments,
  clearFileAttachments,
  onStreamingChange,
  onControlMessage,
  onError,
  onSlashCommands,
  onUserMessageId,
  onLastMessageChange,
  imageCache,
) => {
  const wsRef = useRef(null)
  const queueRef = useRef([])
  const waitersRef = useRef([])
  const modeRef = useRef(mode)
  const optionsRef = useRef(cliOptions)
  const resumeRef = useRef(Boolean(resume))
  const contextFilesRef = useRef(contextFiles)
  const clearContextFilesRef = useRef(clearContextFiles)
  const fileAttachmentsRef = useRef(fileAttachments)
  const clearFileAttachmentsRef = useRef(clearFileAttachments)
  const imageCacheRef = useRef(imageCache)
  const permissionToolRef = useRef(new Map())
  const [sessionName, setSessionName] = useState('New conversation')
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])

  // Keep refs updated
  useEffect(() => {
    modeRef.current = mode
  }, [mode])
  useEffect(() => {
    optionsRef.current = cliOptions
  }, [cliOptions])
  useEffect(() => {
    resumeRef.current = Boolean(resume)
  }, [resume])
  useEffect(() => {
    contextFilesRef.current = contextFiles
  }, [contextFiles])
  useEffect(() => {
    clearContextFilesRef.current = clearContextFiles
  }, [clearContextFiles])
  useEffect(() => {
    fileAttachmentsRef.current = fileAttachments
  }, [fileAttachments])
  useEffect(() => {
    clearFileAttachmentsRef.current = clearFileAttachments
  }, [clearFileAttachments])
  useEffect(() => {
    imageCacheRef.current = imageCache
  }, [imageCache])

  const lastModeRef = useRef(null)
  const lastOptionsKeyRef = useRef(null)
  const lastAttachmentKeyRef = useRef('')

  const connect = useCallback((sessionId, connectMode, resumeOverride, fileSpecsOverride) => {
    const useMode = connectMode || modeRef.current
    const shouldResume =
      typeof resumeOverride === 'boolean' ? resumeOverride : resumeRef.current
    const fileSpecs = Array.isArray(fileSpecsOverride)
      ? fileSpecsOverride
      : (fileAttachmentsRef.current || [])
        .filter((attachment) => attachment?.status === 'ready')
        .map((attachment) => buildFileSpec(attachment))
        .filter(Boolean)
    const fileSpecKey = fileSpecs.join('|')
    const optionsKey = buildRestartKey(optionsRef.current)
    const optionsChanged =
      lastOptionsKeyRef.current !== null && lastOptionsKeyRef.current !== optionsKey
    const attachmentsChanged = fileSpecKey && lastAttachmentKeyRef.current !== fileSpecKey
    lastModeRef.current = useMode
    lastOptionsKeyRef.current = optionsKey

    // Close existing connection if switching sessions or mode
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close()
    }

    return new Promise((resolve, reject) => {
      const shouldForceNew = optionsChanged || attachmentsChanged
      const ws = new WebSocket(
        buildWsUrl(sessionId, useMode, shouldForceNew, shouldResume, optionsRef.current, fileSpecs)
      )
      wsRef.current = ws

      ws.onopen = () => {
        if (wsRef.current !== ws) return
        setIsConnected(true)
        if (fileSpecKey) {
          lastAttachmentKeyRef.current = fileSpecKey
        }
        ws.send(JSON.stringify({
          type: 'control',
          subtype: 'initialize',
          capabilities: {
            permissions: true,
            file_diffs: true,
            user_questions: true,
          },
        }))
        resolve(ws)
      }
      ws.onclose = () => {
        if (wsRef.current !== ws) return
        setIsConnected(false)
      }
      ws.onerror = (event) => {
        if (wsRef.current !== ws) return
        setIsConnected(false)
        onError?.({
          title: 'Connection error',
          detail: 'Unable to reach the Claude CLI backend.',
          suggestions: [
            'Make sure the backend is running.',
            'Try reconnecting or restarting the session.',
          ],
          source: 'connection',
          canRetry: true,
          canRestart: true,
        })
        reject(event)
      }
      ws.onmessage = (event) => {
        if (wsRef.current !== ws) return
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
        if (payload.type === 'system' && payload.subtype === 'error') {
          onError?.({
            title: 'Claude session error',
            detail: payload.message || 'Claude CLI reported an error.',
            suggestions: [
              'Check the CLI output for details.',
              'Try restarting the session.',
            ],
            source: 'session',
            canRetry: true,
            canRestart: true,
          })
        }
        if (payload.type === 'system' && payload.subtype === 'init') {
          if (Array.isArray(payload.slash_commands)) {
            onSlashCommands?.(payload.slash_commands)
          }
        }

        // Handle session_not_found error - restart with a new session
        if (payload.type === 'system' && payload.subtype === 'session_not_found') {
          console.log('[ClaudeStream] Session not found, restarting with new session')
          // Close current connection
          if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
          }
          setIsConnected(false)
          // Generate new session ID and reconnect without resume
          const newSessionId = crypto.randomUUID()
          setCurrentSessionId(newSessionId)
          resumeRef.current = false
          // Connect will be triggered by the state change via useEffect
          return
        }

        if (payload.type === 'control') {
          onControlMessage?.(payload)
        }
        const queue = queueRef.current
        if (queue) {
          queue.push(payload)
          const waiter = waitersRef.current.shift()
          if (waiter) waiter()
        }
      }
    })
  }, [setCurrentSessionId, onControlMessage, onError, onSlashCommands])

  const nextPayload = useCallback(async () => {
    if (queueRef.current.length) return queueRef.current.shift()
    return new Promise((resolve) => {
      waitersRef.current.push(() => resolve(queueRef.current.shift()))
    })
  }, [])

  // Connect proactively on mount or when session changes
  useEffect(() => {
    connect(currentSessionId, mode).catch(() => {
      // Connection failed, will retry on message send
    })
  }, [connect, currentSessionId])

  const switchSession = useCallback((sessionId, resumeOverride = true) => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    connect(sessionId, undefined, resumeOverride).catch(() => {})
  }, [connect])

  // Force restart session (e.g., after permission change)
  const restartSession = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    const fileSpecs = (fileAttachmentsRef.current || [])
      .filter((attachment) => attachment?.status === 'ready')
      .map((attachment) => buildFileSpec(attachment))
      .filter(Boolean)
    // Reconnect with force_new to restart CLI with new settings
    const wsUrl = buildWsUrl(
      currentSessionId,
      modeRef.current,
      true,
      resumeRef.current,
      optionsRef.current,
      fileSpecs,
    ) // force_new=true
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    ws.onopen = () => {
      if (wsRef.current !== ws) return
      setIsConnected(true)
      ws.send(JSON.stringify({
        type: 'control',
        subtype: 'initialize',
        capabilities: {
          permissions: true,
          file_diffs: true,
          user_questions: true,
        },
      }))
    }
    ws.onclose = () => {
      if (wsRef.current !== ws) return
      setIsConnected(false)
    }
    ws.onmessage = (event) => {
      if (wsRef.current !== ws) return
      try {
        const payload = JSON.parse(event.data)
        if (payload.type === 'system' && payload.subtype === 'connected') {
          console.log('[ClaudeStream] Session restarted with new permissions')
        }
        queueRef.current?.push(payload)
        const waiter = waitersRef.current?.shift()
        if (waiter) waiter()
      } catch {
        // Ignore JSON parse errors
      }
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
    const pendingTool = permissionToolRef.current.get(requestId)
    if (pendingTool) {
      if (decision === 'allow') {
        pendingTool.status = 'running'
        setTimeout(() => {
          if (pendingTool.status === 'running') {
            pendingTool.status = 'complete'
          }
        }, 180)
      } else {
        pendingTool.status = 'error'
        pendingTool.error = message || 'Permission denied'
      }
      permissionToolRef.current.delete(requestId)
    }
  }, [])

  const sendQuestionResponse = useCallback((requestId, answers) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('[ClaudeStream] Cannot send question response - WebSocket not connected')
      return
    }
    const response = {
      type: 'control_response',
      request_id: requestId,
      answers: answers || {},
    }
    wsRef.current.send(JSON.stringify(response))
  }, [])

  const sendControlMessage = useCallback((subtype, payload = {}) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('[ClaudeStream] Cannot send control - WebSocket not connected')
      return
    }
    wsRef.current.send(JSON.stringify({
      type: 'control',
      subtype,
      ...payload,
    }))
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
      const userText = findContent(lastUser?.content, (c) => c.type === 'text')?.text || ''
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

      const fileSpecs = (fileAttachmentsRef.current || [])
        .filter((attachment) => attachment?.status === 'ready')
        .map((attachment) => buildFileSpec(attachment))
        .filter(Boolean)
      const ws = await connect(currentSessionId, undefined, undefined, fileSpecs)
      const abortHandler = () => {
        sendControlMessage('interrupt')
      }
      abortSignal?.addEventListener('abort', abortHandler, { once: true })
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
      clearFileAttachmentsRef.current?.()

      const parts = []
      let textPartIndex = -1
      const toolIndex = new Map()
      const toolSignature = new Set()
      const seenUuids = new Set() // Track seen message uuids to avoid duplicates
      let latestCommandOutput = null // Track latest command output (for slash commands, show only the last)
      let hasAssistantText = false
      let running = true
      const scheduleStatusChange = (toolPart, fromStatus, toStatus, delayMs) => {
        setTimeout(() => {
          if (toolPart.status === fromStatus) {
            toolPart.status = toStatus
          }
        }, delayMs)
      }

      while (running) {
        if (abortSignal?.aborted) break
        const payload = await nextPayload()
        if (!payload) continue

        // Log ALL incoming messages
        console.log('[ClaudeStream] <<', payload.type, payload.subtype || '', payload.uuid?.slice(0, 8) || '')

        if (payload.type === 'assistant') {
          const rawContent = payload.message?.content
          if (typeof rawContent === 'string') {
            parts.push({ type: 'text', text: rawContent })
            textPartIndex = parts.length - 1
            hasAssistantText = true
          }
          const content = Array.isArray(rawContent) ? rawContent : []
          content.forEach((part) => {
            if (part.type === 'text' || part.type === 'output_text') {
              if (textPartIndex === -1) {
                parts.push({ type: 'text', text: part.text || '' })
                textPartIndex = parts.length - 1
              } else {
                const existing = parts[textPartIndex]
                existing.text = mergeStreamText(existing.text || '', part.text || '')
              }
              hasAssistantText = true
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
                status: 'pending',
                lineCount: null,
              }
              scheduleStatusChange(toolPart, 'pending', 'running', 120)
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

          const messageId =
            payload.message?.id ||
            payload.message?.message_id ||
            payload.message?.uuid ||
            payload.message_id ||
            payload.uuid
          if (messageId) {
            onUserMessageId?.(messageId)
          }

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

          const toolResult = findContent(payload.message?.content, (c) => c.type === 'tool_result')
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
            if (toolResult.is_error) {
              toolPart.status = 'error'
            } else {
              toolPart.status = 'streaming'
              scheduleStatusChange(toolPart, 'streaming', 'complete', 160)
            }
          }
        }

        // Handle control_request from CLI (interactive permission prompt)
        // This is sent when --permission-prompt-tool stdio is used
        if (payload.type === 'control_request') {
          console.log('[ClaudeStream] Control request detected:', payload)
          const request = payload.request || {}
          const toolName = request.tool_name || request.toolName || 'tool'
          const toolInput = request.input || request.tool_input || request.inputs || {}
          const toolId = request.tool_use_id || payload.request_id || `control-${Date.now()}`
          if (!toolIndex.has(toolId)) {
            const inputKey = toolInput.file_path || toolInput.path || toolInput.command || toolId
            const signature = `${toolName}-${inputKey}`
            if (!toolSignature.has(signature)) {
              const toolPart = {
                type: 'tool_use',
                id: toolId,
                name: toolName,
                input: toolInput,
                output: '',
                status: 'pending',
                lineCount: null,
              }
              toolSignature.add(signature)
              toolIndex.set(toolId, toolPart)
              parts.push(toolPart)
              textPartIndex = -1
              if (payload.request_id) {
                permissionToolRef.current.set(payload.request_id, toolPart)
              }
            }
          }
          onStreamingChange?.({
            type: 'control_request',
            payload,
          })
        }
        if (payload.type === 'control_cancel_request') {
          console.log('[ClaudeStream] Control cancel detected:', payload)
          const requestId = payload.request_id
          if (requestId && permissionToolRef.current.has(requestId)) {
            const toolPart = permissionToolRef.current.get(requestId)
            toolPart.status = 'error'
            toolPart.error = 'Permission request canceled'
            permissionToolRef.current.delete(requestId)
          }
          onStreamingChange?.({
            type: 'control_cancel_request',
            payload,
          })
        }
        if (payload.type === 'control' && payload.subtype === 'user_question_request') {
          console.log('[ClaudeStream] User question request detected:', payload)
          onStreamingChange?.({
            type: 'user_question',
            payload,
          })
        }

        // Also check for explicit permission request messages (if Claude sends them)
        const isPermissionRequest =
          payload.type === 'permission_request' ||
          payload.type === 'approval_request' ||
          payload.type === 'input_request' ||
          payload.type === 'user_input_request' ||
          (payload.type === 'control' && payload.subtype === 'permission_request') ||
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

          const finalText = extractResultText(payload)
          if (finalText && !hasAssistantText) {
            parts.push({ type: 'text', text: finalText })
            textPartIndex = parts.length - 1
          }

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

      abortSignal?.removeEventListener?.('abort', abortHandler)
    },
  }

  return {
    adapter,
    sessionName,
    isConnected,
    switchSession,
    sendApprovalResponse,
    sendQuestionResponse,
    sendMessage,
    restartSession,
    sendControlMessage,
  }
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
        error={part.error}
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
        error={part.error}
        status={part.status}
      />
    )
  }
  if (toolName === 'edit') {
    return (
      <EditToolRenderer
        filePath={input.path || input.file_path}
        diff={input.diff || output}
        error={part.error}
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
      className="claude-message-assistant"
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
                style={{ color: isStreaming ? 'var(--chat-accent)' : 'var(--chat-text-muted)' }}
              >
                ●
              </span>
              <div className="claude-assistant-text">
                <TextBlock text={part.text} />
                {isStreaming && (
                  <span className="claude-streaming-cursor" aria-hidden="true">
                    ▌
                  </span>
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

const mapModeToControl = (mode) => {
  const map = {
    ask: 'default',
    act: 'acceptEdits',
    plan: 'plan',
  }
  return map[mode] || 'default'
}

const mapControlToMode = (mode) => {
  const map = {
    default: 'ask',
    acceptEdits: 'act',
    plan: 'plan',
    bypassPermissions: 'act',
    dontAsk: 'act',
    delegate: 'ask',
  }
  return map[mode] || 'ask'
}

const formatBytes = (value) => {
  const bytes = Number(value || 0)
  if (!bytes || Number.isNaN(bytes)) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`
}

const ImageIcon = () => <Image size={16} aria-hidden="true" />

const FileIcon = () => <FileText size={16} aria-hidden="true" />

const INLINE_IMAGE_LIMIT = 80000

const ComposerShell = ({
  isConnected,
  mode,
  onModeChange,
  showModeMenu,
  setShowModeMenu,
  attachments,
  setAttachments,
  fileAttachments,
  setFileAttachments,
  onAttachFiles,
  isUploadingAttachments,
  contextFiles,
  setContextFiles,
  onRegisterImages,
  slashCommands,
  onError,
}) => {
  const api = useAssistantApi()
  const composerApi = useMemo(() => api.composer(), [api])
  const composerText = useAssistantState(({ composer }) => composer.text)
  const isRunning = useAssistantState(({ thread }) => thread.isRunning)
  const [showSlashMenu, setShowSlashMenu] = useState(false)
  const [showAtMenu, setShowAtMenu] = useState(false)
  const [menuFilter, setMenuFilter] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [menuNavigated, setMenuNavigated] = useState(false)
  const currentMode = MODES.find((item) => item.id === mode) || MODES[0]
  const modeLabel = currentMode?.title || mode
  const modeIcon = (modeLabel || 'M').charAt(0).toUpperCase()

  const inputRef = useRef(null)
  const focusInput = useCallback(() => {
    inputRef.current?.focus?.()
  }, [])

  const applyComposerText = useCallback((nextText) => {
    composerApi?.setText?.(nextText)
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
  }, [composerApi])

  const appendAttachmentsToText = useCallback(() => {
    if (attachments.length === 0) return
    const currentText = composerText || ''
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
  }, [attachments, composerText, setAttachments, applyComposerText, onRegisterImages])
  const slashMenuRef = useRef(null)
  const selectedItemRef = useRef(null)

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

  // Auto-scroll selected menu item into view
  useEffect(() => {
    if ((showSlashMenu || showAtMenu) && selectedItemRef.current) {
      selectedItemRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'nearest',
      })
    }
  }, [selectedIndex, showSlashMenu, showAtMenu])


  const [searchedFiles, setSearchedFiles] = useState([])

  const filteredCommands = (slashCommands || DEFAULT_SLASH_COMMANDS).filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(menuFilter.toLowerCase()) ||
      cmd.description.toLowerCase().includes(menuFilter.toLowerCase())
  )

  // Fetch files when @ menu filter changes
  useEffect(() => {
    if (!showAtMenu) return
    const query = menuFilter || ''
    const controller = new AbortController()
    let timerId = null
    const handleResults = (files) => {
      if (!controller.signal.aborted) {
        setSearchedFiles(files.slice(0, 10))
      }
    }

    if (query.length < 1) {
      timerId = window.setTimeout(() => {
        fetchMentionDefaults(onError).then(handleResults)
      }, 150)
    } else {
      searchFiles(query, onError).then(handleResults)
    }

    return () => {
      controller.abort()
      if (timerId) {
        window.clearTimeout(timerId)
      }
    }
  }, [showAtMenu, menuFilter, onError])

  const handleMenuSelect = (item, type) => {
    if (type === 'at') {
      // Add file to context (if not already added)
      setContextFiles?.((prev) => {
        if (prev.some((f) => f.id === item.id)) return prev
        return [...prev, item]
      })
      // Clear the @ from input
      const currentText = composerText || ''
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
    focusInput()
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
      if (isUploadingAttachments) {
        event.preventDefault()
        return
      }
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
      <div className="claude-input-box" data-mode={mode} ref={slashMenuRef}>
        {(showSlashMenu || showAtMenu) && (
          <div className="claude-menu">
            {showSlashMenu &&
              filteredCommands.map((cmd, idx) => (
                <button
                  key={cmd.id}
                  ref={idx === selectedIndex ? selectedItemRef : null}
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
                  ref={idx === selectedIndex ? selectedItemRef : null}
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
            {showAtMenu && searchedFiles.length === 0 && (
              <div className="claude-menu-empty">Type to search files…</div>
            )}
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
        {fileAttachments?.length > 0 && (
          <div className="claude-file-attachments">
            {fileAttachments.map((file) => (
              <div key={file.id} className={`claude-file-attachment ${file.status || ''}`}>
                <div className="claude-file-meta">
                  <span className="claude-file-name">{file.name || 'attachment'}</span>
                  {file.size ? (
                    <span className="claude-file-size">{formatBytes(file.size)}</span>
                  ) : null}
                </div>
                <div className="claude-file-status">
                  {file.status === 'uploading' && <span>Uploading…</span>}
                  {file.status === 'ready' && <span>Ready</span>}
                  {file.status === 'error' && <span>Error</span>}
                </div>
                <button
                  type="button"
                  onClick={() => setFileAttachments((prev) => prev.filter((item) => item.id !== file.id))}
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
                <span className="claude-context-pill-icon"><FileText size={14} /></span>
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
          asChild
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
        >
          <textarea />
        </ComposerPrimitive.Input>
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
            <label className="claude-icon-button" title="Attach file">
              <FileIcon />
              <input
                type="file"
                className="claude-file-input"
                multiple
                onChange={(event) => {
                  const files = Array.from(event.target.files || [])
                  onAttachFiles?.(files)
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
                const currentText = composerText || ''
                if (!currentText.endsWith('/')) {
                  applyComposerText(`${currentText}/`)
                }
                setShowSlashMenu(true)
                setShowAtMenu(false)
                setSelectedIndex(0)
                setMenuFilter('')
                setMenuNavigated(false)
                setTimeout(() => focusInput(), 0)
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
                const currentText = composerText || ''
                if (!currentText.endsWith('@')) {
                  applyComposerText(`${currentText}@`)
                }
                setShowAtMenu(true)
                setShowSlashMenu(false)
                setSelectedIndex(0)
                setMenuFilter('')
                setMenuNavigated(false)
                setTimeout(() => focusInput(), 0)
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
                        onModeChange?.(item.id)
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
                disabled={!isConnected || isUploadingAttachments}
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

const formatToolSummary = (part) => {
  const name = part?.name || 'Tool'
  const input = part?.input || {}
  const output = part?.output || ''
  const status = part?.status === 'error' ? ' (error)' : ''
  const toolName = String(name)
  let header = toolName

  const path = input.path || input.file_path
  if (toolName.toLowerCase() === 'bash' && input.command) {
    header = `Bash: ${input.command}${status}`
  } else if (toolName.toLowerCase() === 'read' && path) {
    const lines = part?.lineCount ? ` (${part.lineCount} lines)` : ''
    header = `Read: ${path}${lines}${status}`
  } else if ((toolName.toLowerCase() === 'write' || toolName.toLowerCase() === 'edit') && path) {
    header = `${toolName}: ${path}${status}`
  } else if (path) {
    header = `${toolName}: ${path}${status}`
  } else if (status) {
    header = `${toolName}${status}`
  }

  if (output) {
    return `${header}\n\`\`\`\n${output}\n\`\`\``
  }
  return header
}

const normalizeHistoryMessage = (message) => {
  if (!message || (message.role !== 'user' && message.role !== 'assistant')) {
    return null
  }
  const raw = Array.isArray(message.content)
    ? message.content
    : message.content
      ? [{ type: 'text', text: String(message.content) }]
      : []
  const textParts = []

  raw.forEach((part) => {
    if (!part) return
    if (part.type === 'text' || part.type === 'output_text') {
      if (part.text) {
        textParts.push({ type: 'text', text: part.text })
      }
      return
    }
    if (part.type === 'tool_use') {
      const summary = formatToolSummary(part)
      if (summary) {
        textParts.push({ type: 'text', text: summary })
      }
    }
  })

  if (textParts.length === 0) return null
  return {
    role: message.role,
    content: textParts,
  }
}

const HistoryPersister = ({ sessionId }) => {
  const messages = useAssistantState(({ thread }) => thread.messages)
  const isRunning = useAssistantState(({ thread }) => thread.isRunning)

  useEffect(() => {
    if (!sessionId) return
    if (isRunning) return
    const normalized = messages
      .map(normalizeHistoryMessage)
      .filter(Boolean)
      .slice(-HISTORY_LIMIT)
    saveStoredHistory(sessionId, normalized)
  }, [messages, sessionId, isRunning])

  return null
}

const RuntimeProvider = ({ adapter, initialMessages, runtimeKey, children }) => {
  const runtime = useLocalRuntime(adapter, { initialMessages })
  return (
    <AssistantRuntimeProvider key={runtimeKey} runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
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

const buildQuestionAnswers = (questions, answersByQuestion) => {
  if (!Array.isArray(questions)) return {}
  const answers = {}
  questions.forEach((question, index) => {
    const answer = answersByQuestion?.[question.question]
    if (!answer) return
    if (question.multiSelect) {
      const parts = String(answer)
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
      if (parts.length) {
        answers[index] = parts
      }
      return
    }
    answers[index] = String(answer)
  })
  return answers
}

const formatErrorTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const UserMessageWithImages = ({ imageCache }) => {
  const message = useMessage()
  const rawText = findContent(message.content, (part) => part.type === 'text')?.text || ''
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

const ErrorBanner = ({
  error,
  onDismiss,
  onViewLog,
  onRetry,
  onRestart,
}) => {
  if (!error) return null
  const suggestions = Array.isArray(error.suggestions)
    ? error.suggestions
    : (error.suggestion ? [error.suggestion] : [])
  return (
    <div className="claude-error-banner" role="alert">
      <div className="claude-error-header">
        <div className="claude-error-title">{error.title || 'Something went wrong'}</div>
        {error.timestamp && (
          <div className="claude-error-time">{formatErrorTime(error.timestamp)}</div>
        )}
      </div>
      {error.detail && <div className="claude-error-detail">{error.detail}</div>}
      {suggestions.length > 0 && (
        <ul className="claude-error-suggestions">
          {suggestions.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      )}
      <div className="claude-error-actions">
        {error.canRetry && (
          <button type="button" className="claude-error-button" onClick={onRetry}>
            Retry connection
          </button>
        )}
        {error.canRestart && (
          <button type="button" className="claude-error-button ghost" onClick={onRestart}>
            Restart session
          </button>
        )}
        <button type="button" className="claude-error-button ghost" onClick={onViewLog}>
          View log
        </button>
        <button type="button" className="claude-error-button ghost" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  )
}

const ErrorLogModal = ({ isOpen, errors, onClear, onClose }) => {
  if (!isOpen) return null
  return (
    <div className="claude-settings-overlay" onClick={onClose}>
      <div
        className="claude-settings-modal claude-error-log-modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="claude-settings-header">
          <h3>Error log</h3>
          <button type="button" className="claude-settings-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="claude-settings-body">
          {errors.length === 0 ? (
            <div className="claude-error-log-empty">No errors recorded.</div>
          ) : (
            <div className="claude-error-log">
              {errors.map((entry) => (
                <div key={entry.id} className="claude-error-log-item">
                  <div className="claude-error-log-header">
                    <div className="claude-error-log-title">{entry.title}</div>
                    <div className="claude-error-log-time">{formatErrorTime(entry.timestamp)}</div>
                  </div>
                  {entry.detail && (
                    <div className="claude-error-log-detail">{entry.detail}</div>
                  )}
                  {entry.source && (
                    <div className="claude-error-log-source">Source: {entry.source}</div>
                  )}
                  {Array.isArray(entry.suggestions) && entry.suggestions.length > 0 && (
                    <ul className="claude-error-log-suggestions">
                      {entry.suggestions.map((item, index) => (
                        <li key={`${entry.id}-${index}`}>{item}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="claude-settings-actions">
          <button type="button" className="claude-settings-button ghost" onClick={onClear}>
            Clear log
          </button>
          <div className="claude-settings-spacer" />
          <button type="button" className="claude-settings-button ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

const ThinkingIndicator = () => (
  <div className="claude-status" role="status" aria-live="polite">
    <Loader2 className="claude-thinking-spinner" size={16} />
    <span>Thinking...</span>
  </div>
)

const Thread = ({
  sessionLabel,
  activeSessionId,
  isConnected,
  attachments,
  setAttachments,
  fileAttachments,
  setFileAttachments,
  onAttachFiles,
  isUploadingAttachments,
  contextFiles,
  setContextFiles,
  sessions,
  showSessionDropdown,
  setShowSessionDropdown,
  onSelectSession,
  onNewSession,
  showSessionPicker,
  mode,
  onModeChange,
  approvalRequest,
  onApprovalDecision,
  errorBanner,
  onDismissError,
  onViewErrorLog,
  onRetryConnection,
  imageCache,
  onRegisterImages,
  onOpenSettings,
  onRestartSession,
  onOpenRewind,
  slashCommands,
  onError,
}) => {
  const [showModeMenu, setShowModeMenu] = useState(false)
  const [showOverflowMenu, setShowOverflowMenu] = useState(false)
  const sessionDropdownRef = useRef(null)
  const overflowMenuRef = useRef(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!showSessionPicker || !showSessionDropdown) return
    const handleClickOutside = (event) => {
      if (sessionDropdownRef.current && !sessionDropdownRef.current.contains(event.target)) {
        setShowSessionDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showSessionPicker, showSessionDropdown, setShowSessionDropdown])

  useEffect(() => {
    if (!showSessionPicker && showSessionDropdown) {
      setShowSessionDropdown(false)
    }
  }, [showSessionPicker, showSessionDropdown, setShowSessionDropdown])

  // Close overflow menu when clicking outside
  useEffect(() => {
    if (!showOverflowMenu) return
    const handleClickOutside = (event) => {
      if (overflowMenuRef.current && !overflowMenuRef.current.contains(event.target)) {
        setShowOverflowMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showOverflowMenu])

  return (
    <ChatPanel className="chat-panel-light">
      <div className="claude-stream-header">
        <div className="claude-stream-title">
          <Sparkles className="mark" size={16} />
          <span>Claude Code</span>
        </div>
        <div className="claude-stream-header-actions" ref={overflowMenuRef}>
          <button
            type="button"
            className="overflow-menu-btn"
            title="More options"
            onClick={() => setShowOverflowMenu(!showOverflowMenu)}
          >
            <MoreHorizontal size={16} />
          </button>
          {showOverflowMenu && (
            <div className="overflow-menu">
              <button type="button" onClick={() => { onOpenRewind(); setShowOverflowMenu(false); }}>
                <RotateCcw size={14} />
                <span>Rewind files</span>
              </button>
              <button type="button" onClick={() => { onRestartSession(); setShowOverflowMenu(false); }}>
                <RefreshCw size={14} />
                <span>Restart session</span>
              </button>
              <button type="button" onClick={() => { onOpenSettings(); setShowOverflowMenu(false); }}>
                <Settings size={14} />
                <span>Settings</span>
              </button>
            </div>
          )}
        </div>
      </div>
      {errorBanner && (
        <ErrorBanner
          error={errorBanner}
          onDismiss={onDismissError}
          onViewLog={onViewErrorLog}
          onRetry={onRetryConnection}
          onRestart={onRestartSession}
        />
      )}

      {showSessionPicker && (
        <div style={{ position: 'relative' }} ref={sessionDropdownRef}>
          <SessionHeader
            title={sessionLabel}
            onTitleClick={() => setShowSessionDropdown((prev) => !prev)}
            onNewSession={onNewSession}
            showDropdown={true}
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
                    className={`claude-session-item ${s.id === activeSessionId ? 'active' : ''}`}
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
      )}

      <MessageList>
        <EmptyState>
          <div className="claude-stream-empty">
            <Sparkles className="mark" size={24} />
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
        <ThinkingIndicator />
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
        onModeChange={onModeChange}
        showModeMenu={showModeMenu}
        setShowModeMenu={setShowModeMenu}
        attachments={attachments}
        setAttachments={setAttachments}
        fileAttachments={fileAttachments}
        setFileAttachments={setFileAttachments}
        onAttachFiles={onAttachFiles}
        isUploadingAttachments={isUploadingAttachments}
        contextFiles={contextFiles}
        setContextFiles={setContextFiles}
        onRegisterImages={onRegisterImages}
        slashCommands={slashCommands}
        onError={onError}
      />
    </ChatPanel>
  )
}

const SessionSettingsModal = ({ isOpen, options, onClose, onSave }) => {
  const [draft, setDraft] = useState(options)

  useEffect(() => {
    if (isOpen) {
      setDraft(options)
    }
  }, [isOpen, options])

  if (!isOpen) return null

  const updateDraft = (key, value) => {
    setDraft((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="claude-settings-overlay" onClick={onClose}>
      <div
        className="claude-settings-modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="claude-settings-header">
          <div>
            <div className="claude-settings-title">CLI startup options</div>
            <div className="claude-settings-subtitle">
              Applied on restart for this session.
            </div>
          </div>
          <button type="button" className="claude-settings-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="claude-settings-body">
          <label className="claude-settings-label">
            Model
            <input
              className="claude-settings-input"
              value={draft.model}
              onChange={(event) => updateDraft('model', event.target.value)}
              placeholder="claude-sonnet-4-20250514"
            />
          </label>
          <label className="claude-settings-label">
            Max thinking tokens
            <input
              className="claude-settings-input"
              type="number"
              min="0"
              value={draft.maxThinkingTokens}
              onChange={(event) => updateDraft('maxThinkingTokens', event.target.value)}
              placeholder="e.g. 5000"
            />
          </label>
          <label className="claude-settings-label">
            Max turns
            <input
              className="claude-settings-input"
              type="number"
              min="0"
              value={draft.maxTurns}
              onChange={(event) => updateDraft('maxTurns', event.target.value)}
              placeholder="e.g. 20"
            />
          </label>
          <label className="claude-settings-label">
            Max budget (USD)
            <input
              className="claude-settings-input"
              type="number"
              min="0"
              step="0.01"
              value={draft.maxBudgetUsd}
              onChange={(event) => updateDraft('maxBudgetUsd', event.target.value)}
              placeholder="e.g. 1.50"
            />
          </label>
          <label className="claude-settings-label">
            Allowed tools (comma-separated)
            <input
              className="claude-settings-input"
              value={draft.allowedTools}
              onChange={(event) => updateDraft('allowedTools', event.target.value)}
              placeholder="Bash,Read,Write"
            />
          </label>
          <label className="claude-settings-label">
            Disallowed tools (comma-separated)
            <input
              className="claude-settings-input"
              value={draft.disallowedTools}
              onChange={(event) => updateDraft('disallowedTools', event.target.value)}
              placeholder="WebSearch,WebFetch"
            />
          </label>
        </div>
        <div className="claude-settings-actions">
          <button
            type="button"
            className="claude-settings-button ghost"
            onClick={() => setDraft({ ...DEFAULT_CLI_OPTIONS })}
          >
            Reset
          </button>
          <div className="claude-settings-spacer" />
          <button type="button" className="claude-settings-button ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="claude-settings-button primary"
            onClick={() => onSave(draft)}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )
}

const RewindModal = ({
  isOpen,
  lastUserMessage,
  lastUserMessageId,
  status,
  result,
  error,
  onPreview,
  onApply,
  onClose,
}) => {
  if (!isOpen) return null

  const messageText = lastUserMessage?.text || ''
  const previewText = messageText.length > 140 ? `${messageText.slice(0, 140)}…` : messageText
  const fileDiffs = result?.file_diffs || result?.fileDiffs || []
  const canSubmit = Boolean(lastUserMessageId) && status === 'idle'

  return (
    <div className="claude-settings-overlay" onClick={onClose}>
      <div
        className="claude-settings-modal claude-rewind-modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="claude-settings-header">
          <h3>Rewind files</h3>
          <button type="button" className="claude-settings-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="claude-settings-body">
          <div className="claude-rewind-summary">
            <div className="claude-rewind-label">Last user message</div>
            <div className="claude-rewind-text">
              {previewText || 'No recent message'}
            </div>
            {lastUserMessageId && (
              <div className="claude-rewind-id">Message ID: {lastUserMessageId}</div>
            )}
          </div>
          {!lastUserMessageId && (
            <div className="claude-rewind-status">Send a message to enable rewind.</div>
          )}
          {status !== 'idle' && (
            <div className="claude-rewind-status">
              Waiting for Claude CLI… ({status === 'preview' ? 'preview' : 'apply'})
            </div>
          )}
          {error && <div className="claude-rewind-error">{error}</div>}
          {fileDiffs.length > 0 && (
            <div className="claude-rewind-diffs">
              {fileDiffs.map((diff, index) => (
                <div key={`${diff.file_path || diff.filePath || 'file'}-${index}`}>
                  <div className="claude-rewind-file">
                    {diff.file_path || diff.filePath || 'file'}
                  </div>
                  <pre className="claude-rewind-diff">{diff.diff || diff.patch || ''}</pre>
                </div>
              ))}
            </div>
          )}
          {result && fileDiffs.length === 0 && (
            <pre className="claude-rewind-diff">{JSON.stringify(result, null, 2)}</pre>
          )}
        </div>
        <div className="claude-settings-actions">
          <button
            type="button"
            className="claude-settings-button ghost"
            onClick={onPreview}
            disabled={!canSubmit}
          >
            Preview changes
          </button>
          <div className="claude-settings-spacer" />
          <button type="button" className="claude-settings-button ghost" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="claude-settings-button primary"
            onClick={onApply}
            disabled={!canSubmit}
          >
            Rewind files
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ClaudeStreamChat({
  initialSessionId = null,
  provider = 'claude',
  resume = false,
  onSessionStarted,
  showSessionPicker = true,
}) {
  const [attachments, setAttachments] = useState([])
  const [contextFiles, setContextFiles] = useState([])
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(initialSessionId)
  const [showSessionDropdown, setShowSessionDropdown] = useState(false)
  const [mode, setMode] = useState('ask')
  const [cliOptions, setCliOptions] = useState(() => {
    try {
      const raw = localStorage.getItem(CLI_OPTIONS_KEY)
      if (raw) {
        return { ...DEFAULT_CLI_OPTIONS, ...JSON.parse(raw) }
      }
    } catch {
      // Ignore storage errors
    }
    return { ...DEFAULT_CLI_OPTIONS }
  })
  const [fileAttachments, setFileAttachments] = useState([])
  const [showSettings, setShowSettings] = useState(false)
  const [approvalRequest, setApprovalRequest] = useState(null)
  const [imageCache, setImageCache] = useState({})
  const [lastUserMessage, setLastUserMessage] = useState(null)
  const [lastUserMessageId, setLastUserMessageId] = useState(null)
  const [slashCommands, setSlashCommands] = useState(DEFAULT_SLASH_COMMANDS)
  const [showRewindModal, setShowRewindModal] = useState(false)
  const [rewindStatus, setRewindStatus] = useState('idle')
  const [rewindResult, setRewindResult] = useState(null)
  const [rewindError, setRewindError] = useState('')
  const [errorLog, setErrorLog] = useState([])
  const [activeError, setActiveError] = useState(null)
  const [showErrorLog, setShowErrorLog] = useState(false)
  const retryMessageRef = useRef(null)
  const pendingRewindIdRef = useRef(null)
  const modeChangeRef = useRef(false)

  // Update session ID when initialSessionId prop changes
  useEffect(() => {
    if (initialSessionId && initialSessionId !== currentSessionId) {
      setCurrentSessionId(initialSessionId)
    }
  }, [initialSessionId])

  useEffect(() => {
    try {
      localStorage.setItem(CLI_OPTIONS_KEY, JSON.stringify(normalizeStoredOptions(cliOptions)))
    } catch {
      // Ignore storage errors
    }
  }, [cliOptions])

  // Fetch sessions on mount and when dropdown opens
  useEffect(() => {
    if (showSessionDropdown) {
      fetchSessions().then(setSessions)
    }
  }, [showSessionDropdown])

  // Note: Approval polling removed - using native stream-json permission messages instead
  // The hook-based approach can be re-enabled by uncommenting and configuring .claude/settings.json hooks

  const clearContextFiles = useCallback(() => setContextFiles([]), [])
  const clearFileAttachments = useCallback(() => setFileAttachments([]), [])
  const logError = useCallback((payload, options = {}) => {
    const entry = {
      id: payload?.id || `error-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      title: payload?.title || 'Something went wrong',
      detail: payload?.detail || '',
      suggestions: Array.isArray(payload?.suggestions)
        ? payload.suggestions
        : (payload?.suggestion ? [payload.suggestion] : []),
      source: payload?.source || 'ui',
      timestamp: payload?.timestamp || new Date().toISOString(),
      canRetry: Boolean(payload?.canRetry),
      canRestart: Boolean(payload?.canRestart),
    }
    setErrorLog((prev) => [entry, ...prev].slice(0, 50))
    if (options.showBanner !== false) {
      setActiveError(entry)
    }
  }, [])
  const dismissError = useCallback(() => setActiveError(null), [])
  const clearErrorLog = useCallback(() => {
    setErrorLog([])
    setActiveError(null)
  }, [])
  const sendApprovalResponseRef = useRef(null)
  const sendQuestionResponseRef = useRef(null)
  const sendControlMessageRef = useRef(null)
  const handleStreamingChange = useCallback((event) => {
    // Handle boolean (start/stop streaming)
    if (typeof event === 'boolean') {
      if (!event) {
        // Clear any pending approval when stream ends
        setApprovalRequest(null)
      }
      return
    }

    if (event?.type === 'user_question') {
      const payload = event.payload || {}
      const questions = payload.questions || payload.request?.questions || []
      setApprovalRequest({
        id: payload.request_id || payload.id || `question-${Date.now()}`,
        tool_name: 'AskUserQuestion',
        tool_input: {
          questions,
          answers: {},
        },
        source: 'user_question',
      })
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

  const handleControlMessage = useCallback((payload) => {
    const subtype = payload?.subtype
    const pendingRewindId = pendingRewindIdRef.current
    const responsePayload = payload?.response?.subtype ? payload.response : payload
    const isRewindResponse = (
      subtype === 'rewind_files' ||
      payload?.response?.subtype === 'rewind_files' ||
      (pendingRewindId && payload?.request_id === pendingRewindId)
    )

    if (isRewindResponse) {
      setRewindResult(responsePayload)
      setRewindStatus('idle')
      setRewindError('')
      pendingRewindIdRef.current = null
      setShowRewindModal(true)
      return
    }

    if (subtype === 'error' && pendingRewindId && payload?.request_id === pendingRewindId) {
      const errorMessage = payload?.error?.message || payload?.message || 'Rewind failed'
      setRewindError(String(errorMessage))
      setRewindStatus('idle')
      pendingRewindIdRef.current = null
      return
    }
    if (subtype === 'error') {
      logError({
        title: 'Claude control error',
        detail: payload?.error?.message || payload?.message || 'An unknown error occurred.',
        suggestions: [
          'Review the CLI output for details.',
          'Retry the action after reconnecting.',
        ],
        source: 'control',
        canRetry: true,
        canRestart: true,
      })
      return
    }

    if (subtype === 'set_permission_mode') {
      const nextMode = mapControlToMode(payload.mode)
      setMode(nextMode)
      return
    }
    if (subtype === 'set_model') {
      const nextModel = payload.model
      if (nextModel) {
        setCliOptions((prev) => ({ ...prev, model: String(nextModel) }))
      }
      return
    }
    if (subtype === 'set_max_thinking_tokens') {
      if (payload.max_thinking_tokens !== undefined && payload.max_thinking_tokens !== null) {
        setCliOptions((prev) => ({
          ...prev,
          maxThinkingTokens: String(payload.max_thinking_tokens),
        }))
      }
    }
  }, [])

  const handleLastMessageChange = useCallback((msg) => {
    setLastUserMessage(msg)
    retryMessageRef.current = msg
  }, [])

  const handleUserMessageId = useCallback((messageId) => {
    setLastUserMessageId(messageId)
  }, [])

  const handleSlashCommands = useCallback((commands) => {
    setSlashCommands(normalizeSlashCommands(commands))
  }, [])

  const {
    adapter,
    sessionName,
    isConnected,
    switchSession,
    sendApprovalResponse,
    sendQuestionResponse,
    sendMessage,
    restartSession,
    sendControlMessage,
  } = useClaudeStreamRuntime(
    currentSessionId,
    setCurrentSessionId,
    mode,
    cliOptions,
    resume,
    contextFiles,
    clearContextFiles,
    fileAttachments,
    clearFileAttachments,
    handleStreamingChange,
    handleControlMessage,
    logError,
    handleSlashCommands,
    handleUserMessageId,
    handleLastMessageChange,
    imageCache,
  )
  const streamStartedRef = useRef(false)

  useEffect(() => {
    streamStartedRef.current = false
  }, [currentSessionId])

  useEffect(() => {
    if (!isConnected || streamStartedRef.current) return
    streamStartedRef.current = true
    onSessionStarted?.(currentSessionId)
  }, [isConnected, currentSessionId, onSessionStarted])

  // Store sendApprovalResponse in ref for use in callback
  useEffect(() => {
    sendApprovalResponseRef.current = sendApprovalResponse
  }, [sendApprovalResponse])
  useEffect(() => {
    sendQuestionResponseRef.current = sendQuestionResponse
  }, [sendQuestionResponse])
  useEffect(() => {
    sendControlMessageRef.current = sendControlMessage
  }, [sendControlMessage])

  const applyModeChange = useCallback((nextMode) => {
    if (nextMode === mode) return
    modeChangeRef.current = true
    setMode(nextMode)
  }, [mode])

  useEffect(() => {
    if (!modeChangeRef.current) return
    modeChangeRef.current = false
    setTimeout(() => {
      restartSession()
    }, 0)
  }, [mode, restartSession])

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

    if (approvalRequest.source === 'user_question' && sendQuestionResponseRef.current) {
      const input = option.updatedInput || approvalRequest.tool_input || {}
      const questions = input.questions || approvalRequest.tool_input?.questions || []
      const answers = decision === 'deny'
        ? {}
        : buildQuestionAnswers(questions, input.answers)
      sendQuestionResponseRef.current(approvalRequest.id, answers)
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
      applyModeChange(option.nextMode)
    }
    setApprovalRequest(null)
  }, [approvalRequest, mode, applyModeChange])

  const handleSaveSettings = useCallback((nextOptions, onComplete) => {
    const merged = { ...DEFAULT_CLI_OPTIONS, ...nextOptions }
    const previous = normalizeStoredOptions(cliOptions)
    const next = normalizeStoredOptions(merged)
    const requiresRestart = (
      previous.allowedTools !== next.allowedTools ||
      previous.disallowedTools !== next.disallowedTools ||
      previous.maxTurns !== next.maxTurns ||
      previous.maxBudgetUsd !== next.maxBudgetUsd
    )
    const modelChanged = previous.model !== next.model
    const thinkingChanged = previous.maxThinkingTokens !== next.maxThinkingTokens

    setCliOptions(merged)
    setShowSettings(false)

    if (modelChanged && next.model) {
      sendControlMessageRef.current?.('set_model', { model: next.model })
    }
    if (thinkingChanged && next.maxThinkingTokens) {
      const parsed = Number(next.maxThinkingTokens)
      if (!Number.isNaN(parsed)) {
        sendControlMessageRef.current?.('set_max_thinking_tokens', {
          max_thinking_tokens: parsed,
        })
      }
    }

    if (requiresRestart) {
      requestAnimationFrame(() => {
        restartSession()
        onComplete?.()
      })
      return
    }
    onComplete?.()
  }, [cliOptions, restartSession])

  const handleRestartSession = useCallback(() => {
    restartSession()
  }, [restartSession])

  const handleNewSession = useCallback(async () => {
    const newId = await createNewSession()
    if (newId) {
      switchSession(newId, false)
      // Refresh sessions list
      fetchSessions().then(setSessions)
    } else {
      logError({
        title: 'Could not start a new session',
        detail: 'The backend did not return a new session id.',
        suggestions: [
          'Make sure the backend is running.',
          'Retry creating a new session.',
        ],
        source: 'session',
        canRetry: true,
        canRestart: true,
      })
    }
  }, [switchSession, logError])

  const handleSelectSession = useCallback((sessionId) => {
    switchSession(sessionId)
  }, [switchSession])

  const handleAttachFiles = useCallback((files) => {
    const list = Array.from(files || [])
    if (list.length === 0) return

    list.forEach((file) => {
      const tempId = `${Date.now()}-${file.name}-${Math.random().toString(36).slice(2, 6)}`
      setFileAttachments((prev) => [
        ...prev,
        {
          id: tempId,
          name: file.name,
          size: file.size,
          status: 'uploading',
        },
      ])
      uploadAttachment(file)
        .then((data) => {
          setFileAttachments((prev) => prev.map((item) => (
            item.id === tempId
              ? {
                ...item,
                status: 'ready',
                fileId: data.file_id,
                relativePath: data.relative_path,
                name: data.name || file.name,
                size: data.size || file.size,
              }
              : item
          )))
        })
        .catch((error) => {
          setFileAttachments((prev) => prev.map((item) => (
            item.id === tempId
              ? {
                ...item,
                status: 'error',
                error: error?.message || 'Upload failed',
              }
              : item
          )))
          logError({
            title: `Upload failed for ${file.name}`,
            detail: error?.message || 'The file could not be uploaded.',
            suggestions: [
              'Check the file size and permissions.',
              'Try uploading the file again.',
            ],
            source: 'upload',
            canRetry: false,
            canRestart: false,
          })
        })
    })
  }, [logError])
  const handleRegisterImages = useCallback((image) => {
    if (!image?.id) return
    setImageCache((prev) => ({ ...prev, [image.id]: image }))
  }, [])

  const isUploadingAttachments = fileAttachments.some((attachment) => attachment.status === 'uploading')

  const openRewindModal = useCallback(() => {
    setShowRewindModal(true)
  }, [])
  const closeRewindModal = useCallback(() => {
    setShowRewindModal(false)
    setRewindStatus('idle')
    setRewindResult(null)
    setRewindError('')
    pendingRewindIdRef.current = null
  }, [])
  const requestRewind = useCallback((dryRun) => {
    if (!lastUserMessageId) {
      setRewindError('No user message available to rewind.')
      logError({
        title: 'Rewind unavailable',
        detail: 'No user message was found to rewind.',
        suggestions: ['Send a message first, then try again.'],
        source: 'rewind',
        canRetry: false,
        canRestart: false,
      })
      return
    }
    if (!sendControlMessageRef.current) {
      setRewindError('Rewind is unavailable while disconnected.')
      logError({
        title: 'Rewind unavailable',
        detail: 'The session is disconnected.',
        suggestions: ['Reconnect and retry rewind.'],
        source: 'rewind',
        canRetry: true,
        canRestart: true,
      })
      return
    }
    const requestId = `rewind-${Date.now()}`
    pendingRewindIdRef.current = requestId
    setRewindStatus(dryRun ? 'preview' : 'apply')
    setRewindResult(null)
    setRewindError('')
    sendControlMessageRef.current('rewind_files', {
      request_id: requestId,
      user_message_id: lastUserMessageId,
      dry_run: Boolean(dryRun),
    })
  }, [lastUserMessageId, logError])

  const handleRetryConnection = useCallback(() => {
    if (!currentSessionId) return
    switchSession(currentSessionId, true)
    setActiveError(null)
  }, [currentSessionId, switchSession])

  const sessionLabel = useMemo(() => {
    const id = currentSessionId || sessionName
    return formatSessionLabel(id, sessions)
  }, [currentSessionId, sessionName, sessions])

  const historySeed = useMemo(() => {
    const sessionKey = currentSessionId || sessionName
    if (!sessionKey) return []
    return loadStoredHistory(sessionKey)
      .map(normalizeHistoryMessage)
      .filter(Boolean)
  }, [currentSessionId, sessionName])

  const runtimeKey = currentSessionId || sessionName || 'new'

  return (
    <div style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
      <style>{chatThemeVars}</style>
      <RuntimeProvider adapter={adapter} initialMessages={historySeed} runtimeKey={runtimeKey}>
        <HistoryPersister sessionId={currentSessionId || sessionName} />
        <Thread
          sessionLabel={sessionLabel}
          activeSessionId={currentSessionId || sessionName}
          isConnected={isConnected}
          attachments={attachments}
          setAttachments={setAttachments}
          fileAttachments={fileAttachments}
          setFileAttachments={setFileAttachments}
          onAttachFiles={handleAttachFiles}
          isUploadingAttachments={isUploadingAttachments}
          contextFiles={contextFiles}
          setContextFiles={setContextFiles}
          sessions={sessions}
          showSessionDropdown={showSessionDropdown}
          setShowSessionDropdown={setShowSessionDropdown}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          showSessionPicker={showSessionPicker}
          mode={mode}
          onModeChange={applyModeChange}
          approvalRequest={approvalRequest}
          onApprovalDecision={handleApprovalDecision}
          errorBanner={activeError}
          onDismissError={dismissError}
          onViewErrorLog={() => setShowErrorLog(true)}
          onRetryConnection={handleRetryConnection}
          imageCache={imageCache}
          onRegisterImages={handleRegisterImages}
          onOpenSettings={() => setShowSettings(true)}
          onRestartSession={handleRestartSession}
          onOpenRewind={openRewindModal}
          slashCommands={slashCommands}
          onError={logError}
        />
        <SessionSettingsModal
          isOpen={showSettings}
          options={cliOptions}
          onClose={() => setShowSettings(false)}
          onSave={handleSaveSettings}
        />
        <RewindModal
          isOpen={showRewindModal}
          lastUserMessage={lastUserMessage}
          lastUserMessageId={lastUserMessageId}
          status={rewindStatus}
          result={rewindResult}
          error={rewindError}
          onPreview={() => requestRewind(true)}
          onApply={() => requestRewind(false)}
          onClose={closeRewindModal}
        />
        <ErrorLogModal
          isOpen={showErrorLog}
          errors={errorLog}
          onClear={clearErrorLog}
          onClose={() => setShowErrorLog(false)}
        />
      </RuntimeProvider>
    </div>
  )
}
