import { useEffect, useRef } from 'react'
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

const buildWorkflowSocketUrl = (workflowId) => {
  const apiBase = import.meta.env.VITE_API_URL || ''
  let wsBase
  if (apiBase) {
    wsBase = apiBase.replace(/^http/, 'ws')
  } else {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    wsBase = `${protocol}://${window.location.host}`
  }

  const params = new URLSearchParams()
  params.set('provider', 'kurt')
  params.set('kurt_subcommand', 'workflows')
  params.set('kurt_args', JSON.stringify(['follow', workflowId, '--wait']))
  params.set('session_id', `workflow-${workflowId}`)
  params.set('force_new', '1')

  return `${wsBase}/ws/pty?${params}`
}

export default function WorkflowTerminalPanel({ params }) {
  const { workflowId } = params || {}
  const { theme: appTheme } = useTheme()
  const containerRef = useRef(null)
  const termRef = useRef(null)
  const fitAddonRef = useRef(null)
  const socketRef = useRef(null)
  const openedRef = useRef(false)

  // Update terminal theme when app theme changes
  useEffect(() => {
    const term = termRef.current
    if (!term) return
    const newTheme = TERMINAL_THEMES[appTheme] || TERMINAL_THEMES.dark
    term.options.theme = newTheme
  }, [appTheme])

  useEffect(() => {
    if (!containerRef.current || !workflowId) return

    const term = new XTerm({
      cursorBlink: true,
      convertEol: true,
      fontFamily: '"IBM Plex Mono", "SFMono-Regular", Menlo, monospace',
      fontSize: 13,
      theme: TERMINAL_THEMES[appTheme] || TERMINAL_THEMES.dark,
    })

    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    termRef.current = term
    fitAddonRef.current = fitAddon

    let shouldReconnect = true

    const connect = () => {
      const socket = new WebSocket(buildWorkflowSocketUrl(workflowId))
      socketRef.current = socket

      socket.addEventListener('message', (event) => {
        let payload
        try {
          payload = JSON.parse(event.data)
        } catch {
          payload = { type: 'output', data: event.data }
        }

        if (payload.type === 'output' && typeof payload.data === 'string') {
          term.write(payload.data)
        } else if (payload.type === 'error') {
          term.writeln(`\r\n[workflow] Error: ${payload.data}\r\n`)
        } else if (payload.type === 'exit') {
          const code = payload.code ?? 'unknown'
          term.writeln(`\r\n[workflow] Process exited (${code})\r\n`)
        }
      })

      socket.addEventListener('open', () => {
        term.writeln(`[workflow] Attached to workflow ${workflowId.slice(0, 8)}...\r\n`)
        if (fitAddonRef.current) {
          try {
            fitAddon.fit()
            socket.send(
              JSON.stringify({
                type: 'resize',
                cols: term.cols,
                rows: term.rows,
              })
            )
          } catch {
            // Ignore fit errors
          }
        }
      })

      socket.addEventListener('error', () => {
        term.writeln('\r\n[workflow] Connection error\r\n')
      })

      socket.addEventListener('close', () => {
        if (shouldReconnect) {
          term.writeln('\r\n[workflow] Connection closed\r\n')
        }
      })
    }

    const attemptOpen = () => {
      if (openedRef.current) return
      if (!containerRef.current?.isConnected) {
        setTimeout(attemptOpen, 50)
        return
      }

      try {
        term.open(containerRef.current)
        openedRef.current = true
        requestAnimationFrame(() => {
          try {
            fitAddon.fit()
          } catch {
            // Ignore
          }
        })
        connect()
      } catch {
        setTimeout(attemptOpen, 50)
      }
    }

    attemptOpen()

    const handleResize = () => {
      if (fitAddonRef.current && socketRef.current?.readyState === WebSocket.OPEN) {
        try {
          fitAddon.fit()
          socketRef.current.send(
            JSON.stringify({
              type: 'resize',
              cols: term.cols,
              rows: term.rows,
            })
          )
        } catch {
          // Ignore
        }
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      shouldReconnect = false
      if (socketRef.current) {
        socketRef.current.close()
      }
      term.dispose()
    }
  }, [workflowId])

  if (!workflowId) {
    return (
      <div className="panel-content workflow-terminal-panel">
        <div className="workflow-terminal-empty">No workflow ID provided</div>
      </div>
    )
  }

  return (
    <div className="panel-content workflow-terminal-panel">
      <div className="workflow-terminal" ref={containerRef} />
    </div>
  )
}
