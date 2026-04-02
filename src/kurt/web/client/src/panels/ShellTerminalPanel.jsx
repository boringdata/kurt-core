import { useCallback, useEffect, useRef, useState } from 'react'
import { Copy } from 'lucide-react'
import Terminal from '../components/Terminal'

const SESSION_STORAGE_KEY = 'kurt-web-shell-sessions'
const ACTIVE_SESSION_KEY = 'kurt-web-shell-active'

const createSessionId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `shell-${Math.random().toString(36).slice(2)}`
}

const loadSessions = () => {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed) || parsed.length === 0) return null
    return parsed
  } catch {
    return null
  }
}

const loadActiveSession = () => {
  try {
    const raw = localStorage.getItem(ACTIVE_SESSION_KEY)
    if (!raw) return null
    const id = Number(raw)
    return Number.isNaN(id) ? null : id
  } catch {
    return null
  }
}

const normalizeSession = (session, fallbackId) => {
  // eslint-disable-next-line no-unused-vars
  const { bannerMessage, ...rest } = session
  const id = Number(rest.id) || fallbackId
  return {
    ...rest,
    id,
    title: rest.title || `Shell ${id}`,
    provider: 'shell',
    sessionId: rest.sessionId || createSessionId(),
  }
}

const serializeSessions = (sessions) =>
  // eslint-disable-next-line no-unused-vars
  sessions.map(({ bannerMessage, resume, ...session }) => session)

export default function ShellTerminalPanel() {
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
        title: 'Shell 1',
        provider: 'shell',
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
    if (!cleaned) return 'Shell'
    return cleaned.length > 28 ? `${cleaned.slice(0, 28)}…` : cleaned
  }, [])

  const handleFirstPrompt = useCallback(
    (sessionId, prompt) => {
      setSessions((prev) =>
        prev.map((session) => {
          if (session.id !== sessionId) return session
          if (!session.title.startsWith('Shell')) return session
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
      title: `Shell ${nextId}`,
      provider: 'shell',
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
    } catch {
      // Ignore storage errors
    }
  }, [sessions, activeId])

  return (
    <div className="panel-content shell-panel-content">
      <div className="shell-header">
        <div className="shell-session-bar">
          <select
            id="shell-session-select"
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
            <Copy size={14} />
          </button>
          <button
            type="button"
            className="terminal-new terminal-new-icon"
            onClick={addSession}
            aria-label="New shell"
            title="New shell"
          >
            <span aria-hidden="true">+</span>
          </button>
          <button
            type="button"
            className="terminal-close-button"
            onClick={() => closeSession(activeId)}
          >
            Close
          </button>
        </div>
      </div>
      {sessions.length === 0 ? (
        <div className="terminal-empty">
          <p>No active shells.</p>
          <button type="button" className="terminal-new" onClick={addSession}>
            Start new shell
          </button>
        </div>
      ) : (
        <div className="terminal-body">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`terminal-instance ${session.id === activeId ? 'active' : ''}`}
            >
              <Terminal
                key={`${session.id}-${session.sessionId}-${session.resume}`}
                isActive={session.id === activeId}
                provider="shell"
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
      )}
    </div>
  )
}
