import React, { useEffect, useRef } from 'react'
import { Terminal as XTerm } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

const buildSocketUrl = () => {
  const host = import.meta.env.VITE_PTY_HOST || window.location.hostname
  const port = import.meta.env.VITE_PTY_PORT || '8767'
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${host}:${port}`
}

export default function Terminal() {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current) return

    const term = new XTerm({
      cursorBlink: true,
      convertEol: true,
      fontFamily: '"IBM Plex Mono", "SFMono-Regular", Menlo, monospace',
      fontSize: 13,
      theme: {
        background: '#0b0f14',
        foreground: '#e5e7eb',
        cursor: '#f59e0b',
        selection: '#243041',
        green: '#16a34a',
        red: '#ef4444',
        yellow: '#f59e0b',
        blue: '#60a5fa',
        magenta: '#d946ef',
        cyan: '#22d3ee',
        white: '#f3f4f6',
        black: '#0b0f14',
      },
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(containerRef.current)
    fitAddon.fit()
    term.focus()

    const socket = new WebSocket(buildSocketUrl())

    socket.addEventListener('message', (event) => {
      let payload
      try {
        payload = JSON.parse(event.data)
      } catch {
        payload = { type: 'output', data: event.data }
      }

      if (payload.type === 'output' && typeof payload.data === 'string') {
        term.write(payload.data)
      }

      if (payload.type === 'error') {
        term.writeln(`\r\n[bridge] ${payload.data}\r\n`)
      }

      if (payload.type === 'exit') {
        const code = payload.code ?? 'unknown'
        term.writeln(`\r\n[bridge] Claude CLI exited (${code}).\r\n`)
      }
    })

    const sendResize = () => {
      fitAddon.fit()
      socket.send(
        JSON.stringify({
          type: 'resize',
          cols: term.cols,
          rows: term.rows,
        }),
      )
    }

    const resizeListener = () => {
      if (socket.readyState === WebSocket.OPEN) {
        sendResize()
      }
    }

    window.addEventListener('resize', resizeListener)

    term.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data }))
      }
    })

    socket.addEventListener('open', () => {
      sendResize()
    })

    socket.addEventListener('close', () => {
      term.writeln('\r\n[bridge] Connection closed.\r\n')
    })

    return () => {
      window.removeEventListener('resize', resizeListener)
      socket.close()
      term.dispose()
    }
  }, [])

  return <div className="terminal" ref={containerRef} />
}
