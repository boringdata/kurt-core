import { useCallback, useEffect, useRef, useState } from 'react'
import Terminal from '../components/Terminal'
import ClaudeStreamChat from '../components/chat/ClaudeStreamChat'

const SESSION_STORAGE_KEY = 'kurt-web-terminal-sessions'
const VIEW_MODE_KEY = 'kurt-web-terminal-view-mode'
const ACTIVE_SESSION_KEY = 'kurt-web-terminal-active'
const CHAT_INTERFACE_KEY = 'kurt-web-terminal-chat-interface'
const DEFAULT_PROVIDER = 'claude'

const createSessionId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `session-${Math.random().toString(36).slice(2)}`
}

const loadSessions = () => {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed) || parsed.length === 0) return null
    return parsed
  } catch (error) {
    return null
  }
}

const loadActiveSession = () => {
  try {
    const raw = localStorage.getItem(ACTIVE_SESSION_KEY)
    if (!raw) return null
    const id = Number(raw)
    return Number.isNaN(id) ? null : id
  } catch (error) {
    return null
  }
}

const normalizeSession = (session, fallbackId) => {
  const { bannerMessage, ...rest } = session
  const id = Number(rest.id) || fallbackId
  // Always use claude as provider (migration from old codex sessions)
  return {
    ...rest,
    id,
    title: rest.title || `Session ${id}`,
    provider: DEFAULT_PROVIDER,
    sessionId: rest.sessionId || createSessionId(),
  }
}

const serializeSessions = (sessions) =>
  sessions.map(({ bannerMessage, resume, ...session }) => session)

const getFileName = (path) => {
  if (!path) return ''
  const parts = path.split('/')
  return parts[parts.length - 1]
}

export default function TerminalPanel({ params }) {
  const { collapsed, onToggleCollapse, approvals, onFocusReview, onDecision, normalizeApprovalPath } = params || {}
  const terminalCounter = useRef(1)
  // Always in chat mode (removed raw/chat toggle)
  const viewMode = 'chat'
  const [chatInterface, setChatInterface] = useState(() => {
    try {
      return localStorage.getItem(CHAT_INTERFACE_KEY) || 'cli'
    } catch {
      return 'cli'
    }
  })
  const [sessions, setSessions] = useState(() => {
    const saved = loadSessions()
    if (saved) {
      return saved.map((session, index) => ({
        ...normalizeSession(session, index + 1),
        resume: true,
      }))
    }
    return [
      {
        id: 1,
        title: 'Session 1',
        provider: DEFAULT_PROVIDER,
        sessionId: createSessionId(),
        resume: false,
      },
    ]
  })
  const [activeId, setActiveId] = useState(() => {
    const saved = loadActiveSession()
    if (saved) return saved
    if (saved === 0) return 0
    return null
  })

  const formatPrompt = useCallback((prompt) => {
    const cleaned = prompt.replace(/\s+/g, ' ').trim()
    if (!cleaned) return 'Session'
    return cleaned.length > 28 ? `${cleaned.slice(0, 28)}…` : cleaned
  }, [])

  const handleFirstPrompt = useCallback(
    (sessionId, prompt) => {
      setSessions((prev) =>
        prev.map((session) => {
          if (session.id !== sessionId) return session
          if (!session.title.startsWith('Session')) return session
          return { ...session, title: formatPrompt(prompt) }
        }),
      )
    },
    [formatPrompt],
  )

  const addSession = () => {
    const nextId = terminalCounter.current + 1
    terminalCounter.current = nextId
    const next = {
      id: nextId,
      title: `Session ${nextId}`,
      provider: DEFAULT_PROVIDER,
      sessionId: createSessionId(),
      resume: false,
    }
    setSessions((prev) => [...prev, next])
    setActiveId(nextId)
  }

  const closeSession = (id) => {
    setSessions((prev) => {
      if (id == null) return prev
      const next = prev.filter((session) => session.id !== id)
      if (next.length === 0) {
        setActiveId(null)
        return next
      }
      if (id === activeId) {
        setActiveId(next[next.length - 1].id)
      }
      return next
    })
  }

  const handleBannerShown = useCallback((id) => {
    setSessions((prev) =>
      prev.map((session) =>
        session.id === id ? { ...session, bannerMessage: undefined } : session,
      ),
    )
  }, [])

  const handleResumeMissing = useCallback((id) => {
    // Session not found - restart with a new session ID and resume=false
    setSessions((prev) =>
      prev.map((session) =>
        session.id === id
          ? {
              ...session,
              sessionId: createSessionId(),
              resume: false,
            }
          : session,
      ),
    )
  }, [])

  useEffect(() => {
    const maxId = sessions.reduce((max, session) => Math.max(max, session.id), 1)
    terminalCounter.current = maxId
    if (!sessions.length) {
      setActiveId(null)
      return
    }
    if (!sessions.some((session) => session.id === activeId)) {
      setActiveId(sessions[0]?.id || 1)
    }
  }, [sessions, activeId])

  useEffect(() => {
    try {
      if (sessions.length === 0) {
        localStorage.removeItem(SESSION_STORAGE_KEY)
      } else {
        localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(serializeSessions(sessions)))
      }
      if (activeId == null) {
        localStorage.removeItem(ACTIVE_SESSION_KEY)
      } else {
        localStorage.setItem(ACTIVE_SESSION_KEY, String(activeId))
      }
    } catch (error) {
      // Ignore storage errors
    }
  }, [sessions, activeId])

  // Save chat interface preference
  useEffect(() => {
    try {
      localStorage.setItem(CHAT_INTERFACE_KEY, chatInterface)
    } catch {
      // Ignore storage errors
    }
  }, [chatInterface])

  if (collapsed) {
    return (
      <div className="panel-content terminal-panel-content terminal-collapsed">
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={onToggleCollapse}
          title="Expand agent panel"
          aria-label="Expand agent panel"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M10 3.5L5.5 8L10 12.5V3.5Z" />
          </svg>
        </button>
        <div className="sidebar-collapsed-label">Agent</div>
      </div>
    )
  }

  return (
    <div className="panel-content terminal-panel-content">
      <div className="terminal-header">
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={onToggleCollapse}
          title="Collapse agent panel"
          aria-label="Collapse agent panel"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M6 3.5L10.5 8L6 12.5V3.5Z" />
          </svg>
        </button>
        <div className="terminal-title">
          <span className="status-dot" />
          Agent Sessions
        </div>
        <div className="terminal-actions">
          <button
            type="button"
            className="terminal-new terminal-new-icon"
            onClick={addSession}
            aria-label="New session"
            title="New session"
          >
            <span aria-hidden="true">+</span>
          </button>
        </div>
      </div>
      {sessions.length === 0 ? (
        <div className="terminal-empty">
          <p>No active sessions.</p>
          <button type="button" className="terminal-new" onClick={addSession}>
            Start new session
          </button>
        </div>
      ) : (
        <>
          <div className="terminal-session-bar">
            <label htmlFor="terminal-session-select">Session</label>
            <select
              id="terminal-session-select"
              className="terminal-select"
              value={activeId ?? ''}
              onChange={(event) => setActiveId(Number(event.target.value))}
            >
              {sessions.map((session) => (
                <option key={session.id} value={session.id}>
                  {`${session.title} - ${session.sessionId.slice(0, 8)}`}
                </option>
              ))}
            </select>
            {/* CLI/Web toggle */}
            <div className="view-mode-toggle" style={{ marginLeft: '8px' }}>
              <button
                type="button"
                className={`view-mode-btn ${chatInterface === 'cli' ? 'active' : ''}`}
                onClick={() => setChatInterface('cli')}
                title="CLI chat interface"
              >
                CLI
              </button>
              <button
                type="button"
                className={`view-mode-btn ${chatInterface === 'web' ? 'active' : ''}`}
                onClick={() => setChatInterface('web')}
                title="Web chat interface"
              >
                Web
              </button>
            </div>
            <button
              type="button"
              className="terminal-copy-id"
              onClick={() => {
                const active = sessions.find((s) => s.id === activeId)
                if (active?.sessionId) {
                  navigator.clipboard.writeText(active.sessionId)
                }
              }}
              title={sessions.find((s) => s.id === activeId)?.sessionId || 'Copy session ID'}
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z" />
                <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z" />
              </svg>
            </button>
            <button
              type="button"
              className="terminal-close-button"
              onClick={() => closeSession(activeId)}
            >
              Close
            </button>
          </div>
          <div className="terminal-body">
            {sessions.map((session) => {
              const isActive = session.id === activeId
              const className = `terminal-instance${isActive ? ' active' : ''}`

              // CLI: Show PTY terminal stream
              if (chatInterface === 'cli') {
                return (
                  <div key={session.id} className={className}>
                    <Terminal
                      isActive={isActive}
                      provider={session.provider}
                      sessionId={session.sessionId}
                      sessionName={session.title}
                      resume={session.resume}
                      onSessionStarted={() => {
                        setSessions((prev) =>
                          prev.map((s) =>
                            s.id === session.id ? { ...s, resume: true } : s,
                          ),
                        )
                      }}
                      bannerMessage={session.bannerMessage}
                      onBannerShown={() => handleBannerShown(session.id)}
                      onResumeMissing={() => handleResumeMissing(session.id)}
                      onFirstPrompt={(prompt) => handleFirstPrompt(session.id, prompt)}
                    />
                  </div>
                )
              }

              // WEB: Show ClaudeStreamChat
              return (
                <div key={session.id} className={className}>
                  <ClaudeStreamChat
                    initialSessionId={session.sessionId}
                    provider={session.provider}
                    resume={session.resume}
                    showSessionPicker={false}
                    onSessionStarted={(newSessionId) => {
                      if (!newSessionId) return
                      setSessions((prev) =>
                        prev.map((s) =>
                          s.id === session.id
                            ? {
                                ...s,
                                sessionId: newSessionId,
                                resume: true,
                              }
                            : s,
                        ),
                      )
                    }}
                  />
                </div>
              )
            })}
          </div>
        </>
      )}
      {Array.isArray(approvals) && approvals.length > 0 && (
        <div className="review-list">
          <div className="review-list-header">
            <span className="review-list-badge">{approvals.length}</span>
            Pending Reviews
          </div>
          <div className="review-list-items">
            {approvals.map((approval) => {
              const filePath = normalizeApprovalPath?.(approval) || approval.project_path || approval.file_path || ''
              const fileName = getFileName(filePath) || approval.tool_name || 'Review'
              return (
                <div
                  key={approval.id}
                  className="review-list-item"
                  onClick={() => onFocusReview?.(approval.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      onFocusReview?.(approval.id)
                    }
                  }}
                >
                  <div className="review-list-item-info">
                    <span className="review-list-item-name">{fileName}</span>
                    {filePath && <span className="review-list-item-path">{filePath}</span>}
                  </div>
                  <div className="review-list-item-actions">
                    <button
                      type="button"
                      className="review-list-deny"
                      onClick={(e) => {
                        e.stopPropagation()
                        onDecision?.(approval.id, 'deny')
                      }}
                      title="Deny"
                    >
                      ✕
                    </button>
                    <button
                      type="button"
                      className="review-list-allow"
                      onClick={(e) => {
                        e.stopPropagation()
                        onDecision?.(approval.id, 'allow')
                      }}
                      title="Allow"
                    >
                      ✓
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
