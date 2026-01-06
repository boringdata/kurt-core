import { useCallback, useEffect, useRef, useState } from 'react'
import Terminal from '../components/Terminal'

const SESSION_STORAGE_KEY = 'kurt-web-terminal-sessions'
const ACTIVE_SESSION_KEY = 'kurt-web-terminal-active'
const PROVIDERS = [
  { id: 'claude', label: 'Claude' },
  { id: 'codex', label: 'Codex' },
]
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
  const provider =
    typeof rest.provider === 'string' ? rest.provider.toLowerCase() : DEFAULT_PROVIDER
  return {
    ...rest,
    id,
    title: rest.title || `Session ${id}`,
    provider,
    sessionId: rest.sessionId || createSessionId(),
  }
}

const serializeSessions = (sessions) =>
  sessions.map(({ bannerMessage, resume, ...session }) => session)

const getProviderLabel = (provider) => {
  const match = PROVIDERS.find((item) => item.id === provider)
  if (match) return match.label
  if (!provider) return 'Claude'
  return `${provider.charAt(0).toUpperCase()}${provider.slice(1)}`
}

export default function TerminalPanel() {
  const terminalCounter = useRef(1)
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
  const [newProvider, setNewProvider] = useState(DEFAULT_PROVIDER)

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
      provider: newProvider,
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

  return (
    <div className="panel-content terminal-panel-content">
      <div className="terminal-header">
        <div className="terminal-title">
          <span className="status-dot" />
          Agent Sessions
        </div>
        <div className="terminal-actions">
          <select
            id="terminal-provider-select"
            className="terminal-select terminal-provider-select"
            value={newProvider}
            onChange={(event) => setNewProvider(event.target.value)}
            aria-label="Provider"
          >
            {PROVIDERS.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.label}
              </option>
            ))}
          </select>
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
                  {`${session.title} (${getProviderLabel(session.provider)})`}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="terminal-close-button"
              onClick={() => closeSession(activeId)}
            >
              Close
            </button>
          </div>
          <div className="terminal-body">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`terminal-instance ${session.id === activeId ? 'active' : ''}`}
              >
                <Terminal
                  key={`${session.id}-${session.sessionId}-${session.provider}-${session.resume}`}
                  isActive={session.id === activeId}
                  provider={session.provider}
                  sessionId={session.sessionId}
                  sessionName={session.title}
                  resume={Boolean(session.resume)}
                  onFirstPrompt={(prompt) => handleFirstPrompt(session.id, prompt)}
                  onResumeMissing={() => handleResumeMissing(session.id)}
                  bannerMessage={session.bannerMessage}
                  onBannerShown={() => handleBannerShown(session.id)}
                />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
