import React, { useEffect, useRef } from 'react'
import { Terminal as XTerm } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

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
  const containerRef = useRef(null)
  const termRef = useRef(null)
  const fitAddonRef = useRef(null)
  const socketRef = useRef(null)
  const isActiveRef = useRef(isActive)
  const inputBufferRef = useRef('')
  const firstPromptSentRef = useRef(false)
  const sessionStartedRef = useRef(false)
  const historyAppliedRef = useRef(false)
  const openedRef = useRef(false)
  const rendererReadyRef = useRef(false)
  const openAttemptRef = useRef(null)
  const openRetryRef = useRef(null)
  const providerKey = (provider || 'claude').toLowerCase()
  const providerLabel =
    providerKey === 'codex'
      ? 'Codex'
      : providerKey === 'claude'
        ? 'Claude'
        : `${providerKey.charAt(0).toUpperCase()}${providerKey.slice(1)}`

  useEffect(() => {
    isActiveRef.current = isActive
    if (!isActive) return
    if (fitAddonRef.current && termRef.current && openedRef.current) {
      requestAnimationFrame(() => {
        try {
          fitAddonRef.current.fit()
          termRef.current.focus()
        } catch {
          // Ignore fit errors while the terminal is initializing.
        }
      })
    }
    if (!openedRef.current && openAttemptRef.current) {
      openAttemptRef.current()
    }
  }, [isActive])

  useEffect(() => {
    if (!containerRef.current) return

    const term = new XTerm({
      cursorBlink: true,
      convertEol: true,
      fontFamily: '"IBM Plex Mono", "SFMono-Regular", Menlo, monospace',
      fontSize: 13,
      theme: {
        background: '#f8fafc',
        foreground: '#111827',
        cursor: '#111827',
        selection: '#e2e8f0',
        black: '#0f172a',
        red: '#dc2626',
        green: '#16a34a',
        yellow: '#f59e0b',
        blue: '#2563eb',
        magenta: '#db2777',
        cyan: '#0891b2',
        white: '#e2e8f0',
      },
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    termRef.current = term
    fitAddonRef.current = fitAddon

    let shouldReconnect = true
    let reconnectTimer = null
    let connectionStarted = false
    let retryCount = 0
    const MAX_RETRIES = 2

    const connect = () => {
      if (connectionStarted) return
      connectionStarted = true
      historyAppliedRef.current = false
      const socket = new WebSocket(
        buildSocketUrl(sessionId, resume, false, providerKey, sessionName),
      )
      socketRef.current = socket
      let resumeMissingNotified = false

      socket.addEventListener('message', (event) => {
        let payload
        try {
          payload = JSON.parse(event.data)
        } catch {
          payload = { type: 'output', data: event.data }
        }

        if (payload.type === 'session_not_found') {
          if (resume && !resumeMissingNotified) {
            resumeMissingNotified = true
            term.writeln(
              `\r\n[bridge] No saved conversation found. Starting a new session...\r\n`,
            )
            onResumeMissing?.()
          }
          return
        }

        if (payload.type === 'history' && typeof payload.data === 'string') {
          if (!historyAppliedRef.current) {
            historyAppliedRef.current = true
            term.reset()
          }
          term.write(payload.data)
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
            onResumeMissing?.()
          }
          term.write(payload.data)
        }

        if (payload.type === 'error') {
          term.writeln(`\r\n[bridge] ${payload.data}\r\n`)
        }

        if (payload.type === 'exit') {
          const code = payload.code ?? 'unknown'
          term.writeln(`\r\n[bridge] ${providerLabel} CLI exited (${code}).\r\n`)
        }
      })

      socket.addEventListener('open', () => {
        if (isActiveRef.current) {
          sendResize()
        }
        if (onSessionStarted && !sessionStartedRef.current) {
          sessionStartedRef.current = true
          onSessionStarted()
        }
      })

      socket.addEventListener('error', () => {
        term.writeln(`\r\n[bridge] Unable to connect. Is the API server running?\r\n`)
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
        }, 1000)
      })
    }

    const handlePageUnload = () => {
      shouldReconnect = false
      const socket = socketRef.current
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close()
      }
    }

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

    const resizeListener = () => {
      const socket = socketRef.current
      if (socket?.readyState === WebSocket.OPEN && isActiveRef.current) {
        sendResize()
      }
    }

    window.addEventListener('resize', resizeListener)
    window.addEventListener('beforeunload', handlePageUnload)

    const captureFirstPrompt = (data) => {
      if (!onFirstPrompt || firstPromptSentRef.current) return
      const sanitized = data.replace(/\x1b\[[0-9;]*[A-Za-z]/g, '')
      let buffer = inputBufferRef.current

      for (const char of sanitized) {
        if (char === '\r' || char === '\n') {
          const prompt = buffer.trim()
          if (prompt) {
            firstPromptSentRef.current = true
            onFirstPrompt(prompt)
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
      if (openedRef.current || !isActiveRef.current) return
      if (!canOpen()) {
        openRetryRef.current = window.setTimeout(attemptOpen, 60)
        return
      }

      // Suppress xterm.js Viewport race condition errors during initialization.
      const suppressRendererError = (event) => {
        if (
          event.message?.includes('_renderer.value is undefined') ||
          event.message?.includes("can't access property")
        ) {
          event.preventDefault()
          return true
        }
      }
      window.addEventListener('error', suppressRendererError)

      try {
        term.open(containerRef.current)
        openedRef.current = true
      } catch {
        window.removeEventListener('error', suppressRendererError)
        openRetryRef.current = window.setTimeout(attemptOpen, 60)
        return
      }

      const renderSubscription = term.onRender(() => {
        rendererReadyRef.current = true
        renderSubscription.dispose()
        window.removeEventListener('error', suppressRendererError)
        requestAnimationFrame(() => {
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
        })
      })

      setTimeout(() => {
        window.removeEventListener('error', suppressRendererError)
      }, 1000)

      if (bannerMessage) {
        term.writeln(`\r\n[bridge] ${bannerMessage}\r\n`)
        onBannerShown?.()
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
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer)
      }
      if (openRetryRef.current) {
        window.clearTimeout(openRetryRef.current)
      }
      if (socketRef.current) {
        socketRef.current.close()
      }
      term.dispose()
    }
  }, [])

  return <div className="terminal" ref={containerRef} />
}
