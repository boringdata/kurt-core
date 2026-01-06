const fs = require('fs')
const http = require('http')
const path = require('path')
const { spawn } = require('child_process')
const WebSocket = require('ws')
const pty = require('node-pty')

const PORT = parseInt(process.env.KURT_PTY_PORT || '8767', 10)
const CLAUDE_CMD = process.env.KURT_CLAUDE_CMD || 'claude'
const CLAUDE_ARGS = (process.env.KURT_CLAUDE_ARGS || '').split(' ').filter(Boolean)
const WORKDIR = process.env.KURT_PTY_CWD || process.cwd()

const server = http.createServer()
const wss = new WebSocket.Server({ server })

const resolveCommand = (cmd, envPath) => {
  if (cmd.includes(path.sep)) {
    return cmd
  }
  const paths = (envPath || '').split(path.delimiter).filter(Boolean)
  for (const entry of paths) {
    const candidate = path.join(entry, cmd)
    if (fs.existsSync(candidate)) {
      return candidate
    }
  }
  return null
}

const shellEscape = (value) => {
  if (/^[A-Za-z0-9_/:.-]+$/.test(value)) {
    return value
  }
  return `'${value.replace(/'/g, `'\\''`)}'`
}

const spawnClaude = () =>
  pty.spawn(CLAUDE_CMD, CLAUDE_ARGS, {
    name: 'xterm-color',
    cols: 80,
    rows: 24,
    cwd: WORKDIR,
    env: { ...process.env },
  })

const spawnViaShell = () => {
  const shell = process.env.SHELL || '/bin/zsh'
  const command = [CLAUDE_CMD, ...CLAUDE_ARGS].map(shellEscape).join(' ')
  return pty.spawn(shell, ['-lc', command], {
    name: 'xterm-color',
    cols: 80,
    rows: 24,
    cwd: WORKDIR,
    env: { ...process.env },
  })
}

const spawnViaScript = () => {
  const scriptCmd = process.env.KURT_PTY_SCRIPT || 'script'
  const env = {
    ...process.env,
    TERM: process.env.TERM || 'xterm-256color',
    COLORTERM: process.env.COLORTERM || 'truecolor',
    FORCE_COLOR: process.env.FORCE_COLOR || '1',
  }

  if (process.platform === 'darwin') {
    return spawn(scriptCmd, ['-q', '/dev/null', CLAUDE_CMD, ...CLAUDE_ARGS], {
      cwd: WORKDIR,
      env,
    })
  }

  const command = [CLAUDE_CMD, ...CLAUDE_ARGS].map(shellEscape).join(' ')
  return spawn(scriptCmd, ['-q', '-c', command, '/dev/null'], { cwd: WORKDIR, env })
}

const spawnWithoutPty = () => {
  const env = {
    ...process.env,
    TERM: process.env.TERM || 'xterm-256color',
    COLORTERM: process.env.COLORTERM || 'truecolor',
    FORCE_COLOR: process.env.FORCE_COLOR || '1',
  }

  if (CLAUDE_CMD.includes(path.sep)) {
    return spawn(CLAUDE_CMD, CLAUDE_ARGS, { cwd: WORKDIR, env })
  }

  const shell = process.env.SHELL || '/bin/zsh'
  const command = [CLAUDE_CMD, ...CLAUDE_ARGS].map(shellEscape).join(' ')
  return spawn(shell, ['-lc', command], { cwd: WORKDIR, env })
}

const wrapChildProcess = (child) => ({
  type: 'pipe',
  write: (data) => child.stdin && child.stdin.write(data),
  resize: () => {},
  kill: () => child.kill(),
  onData: (cb) => {
    if (child.stdout) {
      child.stdout.on('data', (data) => cb(data.toString()))
    }
    if (child.stderr) {
      child.stderr.on('data', (data) => cb(data.toString()))
    }
  },
  onExit: (cb) => {
    child.on('exit', (code, signal) => cb({ exitCode: code, signal }))
  },
})

wss.on('connection', (ws) => {
  let session

  try {
    session = spawnClaude()
  } catch (error) {
    const resolved = resolveCommand(CLAUDE_CMD, process.env.PATH)
    const executable =
      resolved && fs.existsSync(resolved)
        ? (() => {
            try {
              fs.accessSync(resolved, fs.constants.X_OK)
              return 'yes'
            } catch {
              return 'no'
            }
          })()
        : 'no'
    const hint =
      'Ensure the Claude CLI is installed and executable, or set KURT_CLAUDE_CMD to its full path.'
    const details = [
      `cmd=${CLAUDE_CMD}`,
      `resolved=${resolved || 'not found'}`,
      `executable=${executable}`,
      `cwd=${WORKDIR}`,
    ].join('\n')

    if (process.env.KURT_PTY_SHELL_FALLBACK !== '0') {
      try {
        session = spawnViaShell()
      } catch (shellError) {
        const fallbackError = shellError?.message || shellError
        try {
          const child = spawnViaScript()
          session = wrapChildProcess(child)
          ws.send(
            JSON.stringify({
              type: 'output',
              data: `\r\n[bridge] PTY failed (${fallbackError}). Using script fallback.\r\n`,
            }),
          )
        } catch (pipeError) {
          try {
            const child = spawnWithoutPty()
            session = wrapChildProcess(child)
            ws.send(
              JSON.stringify({
                type: 'output',
                data: `\r\n[bridge] PTY failed (${fallbackError}). Using non-PTY fallback.\r\n`,
              }),
            )
          } catch (finalError) {
            ws.send(
              JSON.stringify({
                type: 'error',
                data: `Failed to start Claude CLI: ${finalError?.message || finalError}\n${hint}\n${details}`,
              }),
            )
            ws.close()
            return
          }
        }
      }
    } else {
      ws.send(
        JSON.stringify({
          type: 'error',
          data: `Failed to start Claude CLI: ${error?.message || error}\n${hint}\n${details}`,
        }),
      )
      ws.close()
      return
    }
  }

  if (session.type === 'pipe') {
    session.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'output', data }))
      }
    })
  } else {
    session.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'output', data }))
      }
    })
  }

  session.onExit(({ exitCode, signal }) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'exit', code: exitCode, signal }))
      ws.close()
    }
  })

  ws.on('message', (message) => {
    let payload
    try {
      payload = JSON.parse(message.toString())
    } catch {
      payload = { type: 'input', data: message.toString() }
    }

    if (payload.type === 'input' && typeof payload.data === 'string') {
      session.write(payload.data)
    }

    if (payload.type === 'resize' && payload.cols && payload.rows) {
      session.resize(payload.cols, payload.rows)
    }
  })

  ws.on('close', () => {
    if (session) {
      session.kill()
    }
  })
})

server.listen(PORT, () => {
  console.log(`Claude PTY bridge listening on ws://localhost:${PORT}`)
})
