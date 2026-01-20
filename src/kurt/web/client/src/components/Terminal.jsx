import React, { useEffect, useRef } from 'react'
import { Terminal as XTerm } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { useTheme } from '../hooks/useTheme'

// Terminal color schemes for light/dark mode
const TERMINAL_THEMES = {
  light: {
    background: '#f8fafc',
    foreground: '#111827',
    cursor: '#111827',
    selectionBackground: '#bfdbfe',
    black: '#0f172a',
    red: '#dc2626',
    green: '#16a34a',
    yellow: '#f59e0b',
    blue: '#2563eb',
    magenta: '#db2777',
    cyan: '#0891b2',
    white: '#e2e8f0',
  },
  dark: {
    background: '#0f172a',
    foreground: '#e2e8f0',
    cursor: '#e2e8f0',
    selectionBackground: '#334155',
    black: '#0f172a',
    red: '#ef4444',
    green: '#22c55e',
    yellow: '#f59e0b',
    blue: '#3b82f6',
    magenta: '#ec4899',
    cyan: '#06b6d4',
    white: '#f1f5f9',
  },
}

const HISTORY_STORAGE_PREFIX = 'kurt-web-pty-history'
const HISTORY_LIMIT_BYTES = 200000

const getHistoryKey = (sessionId) => {
  if (!sessionId) return null
  return `${HISTORY_STORAGE_PREFIX}-${sessionId}`
}

const loadStoredHistory = (sessionId) => {
  const key = getHistoryKey(sessionId)
  if (!key) return ''
  try {
    const raw = localStorage.getItem(key)
    return typeof raw === 'string' ? raw : ''
  } catch {
    return ''
  }
}

const saveStoredHistory = (sessionId, text) => {
  const key = getHistoryKey(sessionId)
  if (!key) return
  const normalized = text.length > HISTORY_LIMIT_BYTES
    ? text.slice(-HISTORY_LIMIT_BYTES)
    : text
  try {
    localStorage.setItem(key, normalized)
  } catch {
    // Ignore storage errors
  }
}

const buildSocketUrl = (sessionId, resume, forceNew, provider, sessionName) => {
  const apiBase = import.meta.env.VITE_API_URL || ''
  let wsBase
  if (apiBase) {
    wsBase = apiBase.replace(/^http/, 'ws')
  } else {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    wsBase = `${protocol}://${window.location.host}`
  }

  const params = new URLSearchParams()
  if (sessionId) {
    params.set('session_id', sessionId)
  }
  if (resume) {
    params.set('resume', '1')
  }
  if (forceNew) {
    params.set('force_new', '1')
  }
  if (provider) {
    params.set('provider', provider)
  }
  if (sessionName) {
    params.set('session_name', sessionName)
  }
  const query = params.toString()
  return `${wsBase}/ws/pty${query ? `?${query}` : ''}`
}

export default function Terminal({
  isActive = true,
  onFirstPrompt,
  provider = 'claude',
  sessionId,
  sessionName,
  resume,
  onSessionStarted,
  onResumeMissing,
  bannerMessage,
  onBannerShown,
}) {
  const { theme: appTheme } = useTheme()
  const containerRef = useRef(null)
  const termRef = useRef(null)
  const fitAddonRef = useRef(null)
  const socketRef = useRef(null)
  const isActiveRef = useRef(isActive)
  const onFirstPromptRef = useRef(onFirstPrompt)
  const onSessionStartedRef = useRef(onSessionStarted)
  const onResumeMissingRef = useRef(onResumeMissing)
  const onBannerShownRef = useRef(onBannerShown)
  const inputBufferRef = useRef('')
  const firstPromptSentRef = useRef(false)
  const sessionStartedRef = useRef(false)
  const historyAppliedRef = useRef(false)
  const openedRef = useRef(false)
  const rendererReadyRef = useRef(false)
  const openAttemptRef = useRef(null)
  const openRetryRef = useRef(null)
  const renderFallbackRef = useRef(null)
  const resizeObserverRef = useRef(null)
  const historyBufferRef = useRef('')
  const historyFallbackTimerRef = useRef(null)
  const historySourceRef = useRef(null)
  // Always use Claude as provider
  const providerKey = 'claude'
  const providerLabel = 'Claude'

  useEffect(() => {
    isActiveRef.current = isActive
    if (!isActive) return
    if (fitAddonRef.current && termRef.current && openedRef.current && rendererReadyRef.current) {
      // Double requestAnimationFrame to ensure renderer is stable
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          try {
            // Extra guard: check if terminal element is still in DOM
            if (!containerRef.current?.isConnected) return
            fitAddonRef.current.fit()
            termRef.current.focus()
          } catch {
            // Ignore fit errors while the terminal is initializing.
          }
        })
      })
    }
    if (!openedRef.current && openAttemptRef.current) {
      openAttemptRef.current()
    }
  }, [isActive])

  useEffect(() => {
    onFirstPromptRef.current = onFirstPrompt
    onSessionStartedRef.current = onSessionStarted
    onResumeMissingRef.current = onResumeMissing
    onBannerShownRef.current = onBannerShown
  }, [onFirstPrompt, onSessionStarted, onResumeMissing, onBannerShown])

  // Update terminal theme when app theme changes
  useEffect(() => {
    if (termRef.current) {
      termRef.current.options.theme = TERMINAL_THEMES[appTheme] || TERMINAL_THEMES.light
    }
  }, [appTheme])

  useEffect(() => {
    if (!containerRef.current) return

    openedRef.current = false
    rendererReadyRef.current = false
    sessionStartedRef.current = false
    firstPromptSentRef.current = false
    inputBufferRef.current = ''
    historyBufferRef.current = ''
    historySourceRef.current = null

    const term = new XTerm({
      cursorBlink: true,
      convertEol: false,
      fontFamily: '"IBM Plex Mono", "SFMono-Regular", Menlo, monospace',
      fontSize: 13,
      theme: TERMINAL_THEMES[appTheme] || TERMINAL_THEMES.light,
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    termRef.current = term
    fitAddonRef.current = fitAddon

    let shouldReconnect = true
    let reconnectTimer = null
    let connectionStarted = false
    let retryCount = 0
    let disposed = false
    const MAX_RETRIES = 10
    const INITIAL_RETRY_DELAY = 500
    const storedHistory = loadStoredHistory(sessionId)
    historyBufferRef.current = storedHistory

    const sendResize = () => {
      if (!isActiveRef.current || !openedRef.current) return
      if (!containerRef.current) return
      if (containerRef.current.clientWidth === 0 || containerRef.current.clientHeight === 0) {
        return
      }
      if (!rendererReadyRef.current) return
      try {
        fitAddon.fit()
      } catch {
        return
      }
      const socket = socketRef.current
      if (!socket || socket.readyState !== WebSocket.OPEN) return
      socket.send(
        JSON.stringify({
          type: 'resize',
          cols: term.cols,
          rows: term.rows,
        }),
      )
    }

    const connect = () => {
      if (connectionStarted) return
      connectionStarted = true
      historyAppliedRef.current = false
      const socket = new WebSocket(
        buildSocketUrl(sessionId, resume, false, providerKey, sessionName),
      )
      socketRef.current = socket
      let resumeMissingNotified = false

      const applyHistory = (source, chunk) => {
        if (!chunk) return
        if (!historyAppliedRef.current) {
          historyAppliedRef.current = true
          historySourceRef.current = source
          historyBufferRef.current = ''
          term.reset()
        }
        historyBufferRef.current += chunk
        if (historyBufferRef.current.length > HISTORY_LIMIT_BYTES) {
          historyBufferRef.current = historyBufferRef.current.slice(-HISTORY_LIMIT_BYTES)
        }
        term.write(chunk)
        saveStoredHistory(sessionId, historyBufferRef.current)
      }

      const appendOutput = (chunk) => {
        if (!chunk) return
        historyBufferRef.current += chunk
        if (historyBufferRef.current.length > HISTORY_LIMIT_BYTES) {
          historyBufferRef.current = historyBufferRef.current.slice(-HISTORY_LIMIT_BYTES)
        }
        term.write(chunk)
        saveStoredHistory(sessionId, historyBufferRef.current)
      }

      const handlePayload = (payload) => {
        if (payload.type === 'session_not_found') {
          if (resume && !resumeMissingNotified) {
            resumeMissingNotified = true
            term.writeln(
              `\r\n[bridge] No saved conversation found. Starting a new session...\r\n`,
            )
            onResumeMissingRef.current?.()
          }
          return
        }

        if (payload.type === 'history' && typeof payload.data === 'string') {
          if (historySourceRef.current === 'local') {
            return
          }
          if (historyFallbackTimerRef.current) {
            window.clearTimeout(historyFallbackTimerRef.current)
            historyFallbackTimerRef.current = null
          }
          applyHistory('server', payload.data)
          return
        }

        if (payload.type === 'output' && typeof payload.data === 'string') {
          if (
            resume &&
            !resumeMissingNotified &&
            payload.data.includes('No conversation found with session ID')
          ) {
            resumeMissingNotified = true
            term.writeln(
              `\r\n[bridge] No saved conversation found. Starting a new session...\r\n`,
            )
            onResumeMissingRef.current?.()
          }
          appendOutput(payload.data)
        }

        if (payload.type === 'error') {
          term.writeln(`\r\n[bridge] ${payload.data}\r\n`)
        }

        if (payload.type === 'exit') {
          const code = payload.code ?? 'unknown'
          term.writeln(`\r\n[bridge] ${providerLabel} CLI exited (${code}).\r\n`)
        }
      }

      const handleRaw = (raw) => {
        let payload
        try {
          payload = JSON.parse(raw)
        } catch {
          payload = { type: 'output', data: raw }
        }
        handlePayload(payload)
      }

      socket.addEventListener('message', (event) => {
        const data = event.data
        if (typeof data === 'string') {
          handleRaw(data)
          return
        }
        if (data instanceof ArrayBuffer) {
          handleRaw(new TextDecoder().decode(data))
          return
        }
        if (data instanceof Blob) {
          data
            .text()
            .then(handleRaw)
            .catch(() => {
              handleRaw('')
            })
          return
        }
        handleRaw(String(data ?? ''))
      })

      socket.addEventListener('open', () => {
        if (isActiveRef.current) {
          sendResize()
        }
        if (onSessionStartedRef.current && !sessionStartedRef.current) {
          sessionStartedRef.current = true
          onSessionStartedRef.current()
        }
        if (storedHistory && !historyAppliedRef.current) {
          historyFallbackTimerRef.current = window.setTimeout(() => {
            if (historyAppliedRef.current || historySourceRef.current === 'server') return
            historySourceRef.current = 'local'
            historyAppliedRef.current = true
            historyBufferRef.current = storedHistory
            term.reset()
            term.write(storedHistory)
          }, 200)
        }
      })

      socket.addEventListener('error', () => {
        // Only show error message after a few retries to avoid spam during startup
        if (retryCount >= 3) {
          term.writeln(`\r\n[bridge] Unable to connect. Retrying...\r\n`)
        }
      })

      socket.addEventListener('close', () => {
        if (!shouldReconnect) return
        retryCount++
        if (retryCount > MAX_RETRIES) {
          term.writeln(`\r\n[bridge] Max retries reached. Click "New session" to try again.\r\n`)
          return
        }
        reconnectTimer = window.setTimeout(() => {
          connectionStarted = false
          connect()
        }, INITIAL_RETRY_DELAY)
      })
    }

    const handlePageUnload = () => {
      shouldReconnect = false
      const socket = socketRef.current
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close()
      }
    }

    const resizeListener = () => {
      const socket = socketRef.current
      if (socket?.readyState === WebSocket.OPEN && isActiveRef.current) {
        sendResize()
      }
    }

    const resizeObserver =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => {
            if (!isActiveRef.current) return
            sendResize()
          })
        : null

    if (resizeObserver) {
      resizeObserver.observe(containerRef.current)
      resizeObserverRef.current = resizeObserver
    }

    window.addEventListener('resize', resizeListener)
    window.addEventListener('beforeunload', handlePageUnload)

    const captureFirstPrompt = (data) => {
      if (!onFirstPromptRef.current || firstPromptSentRef.current) return
      // eslint-disable-next-line no-control-regex
      const sanitized = data.replace(/\x1b\[[0-9;]*[A-Za-z]/g, '')
      let buffer = inputBufferRef.current

      for (const char of sanitized) {
        if (char === '\r' || char === '\n') {
          const prompt = buffer.trim()
          if (prompt) {
            firstPromptSentRef.current = true
            onFirstPromptRef.current(prompt)
          }
          buffer = ''
        } else if (char === '\u007f') {
          buffer = buffer.slice(0, -1)
        } else {
          buffer += char
        }
      }

      inputBufferRef.current = buffer
    }

    term.onData((data) => {
      captureFirstPrompt(data)
      const socket = socketRef.current
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data }))
      }
    })

    const canOpen = () => {
      if (!containerRef.current) return false
      if (!containerRef.current.isConnected) return false
      const rects = containerRef.current.getClientRects()
      if (!rects.length) return false
      if (containerRef.current.clientWidth === 0 || containerRef.current.clientHeight === 0) {
        return false
      }
      const style = window.getComputedStyle(containerRef.current)
      if (style.visibility === 'hidden' || style.display === 'none') {
        return false
      }
      return true
    }

    const attemptOpen = () => {
      if (disposed || openedRef.current || !isActiveRef.current) return
      if (!canOpen()) {
        openRetryRef.current = window.setTimeout(attemptOpen, 60)
        return
      }

      try {
        term.open(containerRef.current)
        openedRef.current = true
      } catch {
        openRetryRef.current = window.setTimeout(attemptOpen, 60)
        return
      }

      const finalizeRenderer = () => {
        if (rendererReadyRef.current || disposed) return
        rendererReadyRef.current = true
        try {
          fitAddon.fit()
          if (isActiveRef.current) {
            term.focus()
          }
        } catch {
          // Ignore fit errors while the renderer is initializing.
        }
        if (isActiveRef.current) {
          sendResize()
        }
      }

      // Wait for renderer to be fully ready before marking as ready.
      // Use multiple frames to ensure xterm's internal state is settled.
      const renderSubscription = term.onRender(() => {
        renderSubscription.dispose()
        if (renderFallbackRef.current) {
          window.clearTimeout(renderFallbackRef.current)
          renderFallbackRef.current = null
        }
        // Double requestAnimationFrame to ensure renderer is fully initialized.
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            finalizeRenderer()
          })
        })
      })

      renderFallbackRef.current = window.setTimeout(() => {
        finalizeRenderer()
      }, 120)

      if (document?.fonts?.ready) {
        document.fonts.ready.then(() => {
          if (disposed || !openedRef.current) return
          try {
            fitAddon.fit()
          } catch {
            // Ignore fit errors while the renderer is initializing.
          }
          if (isActiveRef.current) {
            sendResize()
          }
        })
      }

      connect()
    }

    openAttemptRef.current = attemptOpen

    if (isActiveRef.current) {
      attemptOpen()
    }

    return () => {
      window.removeEventListener('resize', resizeListener)
      window.removeEventListener('beforeunload', handlePageUnload)
      shouldReconnect = false
      disposed = true
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer)
      }
      if (openRetryRef.current) {
        window.clearTimeout(openRetryRef.current)
      }
      if (renderFallbackRef.current) {
        window.clearTimeout(renderFallbackRef.current)
        renderFallbackRef.current = null
      }
      if (historyFallbackTimerRef.current) {
        window.clearTimeout(historyFallbackTimerRef.current)
        historyFallbackTimerRef.current = null
      }
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect()
        resizeObserverRef.current = null
      }
      if (socketRef.current) {
        socketRef.current.close()
      }
      term.dispose()
    }
  }, [providerKey, sessionId, sessionName, resume])

  useEffect(() => {
    if (!bannerMessage) return
    const term = termRef.current
    if (!term) return
    term.writeln(`\r\n[bridge] ${bannerMessage}\r\n`)
    onBannerShownRef.current?.()
  }, [bannerMessage])

  // Update terminal theme when app theme changes
  useEffect(() => {
    const term = termRef.current
    if (!term) return
    const newTheme = TERMINAL_THEMES[appTheme] || TERMINAL_THEMES.light
    term.options.theme = newTheme
  }, [appTheme])

  return (
    <div
      className="terminal"
      ref={containerRef}
      tabIndex={0}
      onMouseDown={() => termRef.current?.focus()}
    />
  )
}
