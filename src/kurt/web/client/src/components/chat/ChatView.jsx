import { useState, useEffect, useRef, useCallback } from 'react'
import { chatThemeVars } from './ChatPanel'
import usePtyMessages from './usePtyMessages'

/**
 * ChatView - Chat UI that connects to PTY WebSocket
 *
 * Props:
 * - socket: WebSocket instance (shared with Terminal)
 * - sessionId: Current session ID
 * - onSendInput: Callback to send input to PTY
 */

// Sample files for @ menu (TODO: fetch from API)
const SAMPLE_FILES = [
  { name: 'package.json', path: 'package.json', isDirectory: false },
  { name: 'src/', path: 'src', isDirectory: true },
  { name: 'README.md', path: 'README.md', isDirectory: false },
  { name: 'vite.config.ts', path: 'vite.config.ts', isDirectory: false },
]

// Sample commands for / menu
const SAMPLE_COMMANDS = [
  {
    label: 'Claude Commands',
    items: [
      { id: 'help', label: '/help', description: 'Show available commands' },
      { id: 'clear', label: '/clear', description: 'Clear the chat' },
      { id: 'compact', label: '/compact', description: 'Compact conversation' },
    ],
  },
  {
    label: 'Project Commands',
    items: [
      { id: 'init', label: '/init', description: 'Initialize project' },
      { id: 'cost', label: '/cost', description: 'Show token usage' },
    ],
  },
]

const ChatView = ({ socket, sessionId, onSendInput }) => {
  const { messages, isStreaming, onUserInput, onPtyOutput, onHistory, reset } =
    usePtyMessages()
  const [inputValue, setInputValue] = useState('')
  const [showAtMenu, setShowAtMenu] = useState(false)
  const [showSlashMenu, setShowSlashMenu] = useState(false)
  const [menuFilter, setMenuFilter] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Listen to WebSocket messages
  useEffect(() => {
    if (!socket) return

    const handleMessage = (event) => {
      try {
        const payload = JSON.parse(event.data)

        if (payload.type === 'output') {
          onPtyOutput(payload.data)
        }

        if (payload.type === 'history') {
          onHistory(payload.data)
        }
      } catch (e) {
        // Non-JSON message, treat as raw output
        onPtyOutput(event.data)
      }
    }

    socket.addEventListener('message', handleMessage)
    return () => socket.removeEventListener('message', handleMessage)
  }, [socket, onPtyOutput, onHistory])

  // Reset when session changes
  useEffect(() => {
    reset()
  }, [sessionId, reset])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Filter files based on menu filter
  const filteredFiles = SAMPLE_FILES.filter((f) =>
    f.name.toLowerCase().includes(menuFilter.toLowerCase())
  )

  // Flatten commands for navigation
  const flattenedCommands = SAMPLE_COMMANDS.flatMap((group) => group.items || [])
  const filteredCommands = flattenedCommands.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(menuFilter.toLowerCase()) ||
      cmd.description?.toLowerCase().includes(menuFilter.toLowerCase())
  )

  // Handle sending a message
  const handleSend = useCallback(() => {
    const text = inputValue.trim()
    if (!text || !socket || socket.readyState !== WebSocket.OPEN) return

    // Track user input for message parsing
    onUserInput(text)
    onUserInput('\r')

    // Send to PTY via WebSocket
    socket.send(JSON.stringify({ type: 'input', data: text + '\r' }))

    setInputValue('')
    setShowAtMenu(false)
    setShowSlashMenu(false)
  }, [inputValue, socket, onUserInput])

  // Handle input change - detect @ and / triggers
  const handleInputChange = useCallback((e) => {
    const newValue = e.target.value
    const lastChar = newValue.slice(-1)
    const prevChar = newValue.slice(-2, -1)

    setInputValue(newValue)

    // Detect @ trigger
    if (lastChar === '@' && (prevChar === '' || prevChar === ' ')) {
      setShowAtMenu(true)
      setShowSlashMenu(false)
      setMenuFilter('')
      setSelectedIndex(0)
    }
    // Detect / trigger at start or after space
    else if (lastChar === '/' && (prevChar === '' || prevChar === ' ')) {
      setShowSlashMenu(true)
      setShowAtMenu(false)
      setMenuFilter('')
      setSelectedIndex(0)
    }
    // Update filter while menu is open
    else if (showAtMenu || showSlashMenu) {
      const triggerChar = showAtMenu ? '@' : '/'
      const lastTriggerIndex = newValue.lastIndexOf(triggerChar)
      if (lastTriggerIndex >= 0) {
        setMenuFilter(newValue.slice(lastTriggerIndex + 1))
      }
      // Close menu if trigger character was deleted
      if (lastTriggerIndex === -1) {
        setShowAtMenu(false)
        setShowSlashMenu(false)
      }
    }
  }, [showAtMenu, showSlashMenu])

  // Handle menu selection
  const handleMenuSelect = useCallback(
    (item) => {
      const triggerChar = showAtMenu ? '@' : '/'
      const lastIndex = inputValue.lastIndexOf(triggerChar)
      const prefix = lastIndex >= 0 ? inputValue.slice(0, lastIndex) : inputValue

      if (showAtMenu) {
        // Insert file path
        setInputValue(prefix + '@' + item.path + ' ')
      } else {
        // Insert command
        setInputValue(prefix + item.label + ' ')
      }

      setShowAtMenu(false)
      setShowSlashMenu(false)
      inputRef.current?.focus()
    },
    [inputValue, showAtMenu]
  )

  // Handle key press
  const handleKeyDown = useCallback(
    (e) => {
      // Menu navigation
      if (showAtMenu || showSlashMenu) {
        const items = showAtMenu ? filteredFiles : filteredCommands
        if (e.key === 'ArrowDown') {
          e.preventDefault()
          setSelectedIndex((prev) => Math.min(prev + 1, items.length - 1))
          return
        } else if (e.key === 'ArrowUp') {
          e.preventDefault()
          setSelectedIndex((prev) => Math.max(prev - 1, 0))
          return
        } else if (e.key === 'Enter' && items.length > 0) {
          e.preventDefault()
          handleMenuSelect(items[selectedIndex])
          return
        } else if (e.key === 'Escape') {
          e.preventDefault()
          setShowAtMenu(false)
          setShowSlashMenu(false)
          return
        } else if (e.key === 'Tab') {
          e.preventDefault()
          if (items.length > 0) {
            handleMenuSelect(items[selectedIndex])
          }
          return
        }
      }

      // Send on Enter (without shift)
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend, handleMenuSelect, showAtMenu, showSlashMenu, filteredFiles, filteredCommands, selectedIndex]
  )

  const isConnected = socket && socket.readyState === WebSocket.OPEN
  const canSend = inputValue.trim() && isConnected

  return (
    <>
      <style>{chatThemeVars}</style>
      {/* Assistant message styles removed with legacy component */}
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          backgroundColor: 'var(--chat-bg, #1e1e1e)',
          color: 'var(--chat-text, #cccccc)',
          fontFamily:
            'var(--font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif)',
        }}
      >
        {/* Messages area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: 'var(--chat-spacing-lg, 16px)',
          }}
        >
          {messages.length === 0 ? (
            <EmptyState isConnected={isConnected} />
          ) : (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--chat-spacing-md, 12px)',
              }}
            >
              {messages.map((message) =>
                message.role === 'user' ? (
                  <UserMessageSimple key={message.id} message={message} />
                ) : (
                  <AssistantMessageSimple
                    key={message.id}
                    message={message}
                    isStreaming={message.isStreaming}
                  />
                )
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input area with menus */}
        <div
          style={{
            padding: 'var(--chat-spacing-md, 12px)',
            borderTop: '1px solid var(--chat-border, #454545)',
            position: 'relative',
          }}
        >
          {/* @ File Menu */}
          {showAtMenu && filteredFiles.length > 0 && (
            <FileMenu
              files={filteredFiles}
              selectedIndex={selectedIndex}
              onSelect={handleMenuSelect}
            />
          )}

          {/* / Command Menu */}
          {showSlashMenu && filteredCommands.length > 0 && (
            <CommandMenu
              commands={filteredCommands}
              selectedIndex={selectedIndex}
              onSelect={handleMenuSelect}
            />
          )}

          <div
            style={{
              display: 'flex',
              gap: '8px',
              alignItems: 'flex-end',
              backgroundColor: 'var(--chat-input-bg, #3c3c3c)',
              borderRadius: 'var(--chat-radius-md, 8px)',
              padding: '10px 12px',
            }}
          >
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={isConnected ? 'Type @ for files, / for commands...' : 'Connecting...'}
              rows={1}
              disabled={!isConnected}
              style={{
                flex: 1,
                backgroundColor: 'transparent',
                border: 'none',
                outline: 'none',
                color: 'var(--chat-text, #cccccc)',
                fontSize: '14px',
                fontFamily: 'inherit',
                resize: 'none',
                lineHeight: '1.4',
                opacity: isConnected ? 1 : 0.5,
              }}
            />
            <button
              onClick={handleSend}
              disabled={!canSend}
              style={{
                backgroundColor: canSend ? '#ae5630' : '#555',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                width: '32px',
                height: '32px',
                cursor: canSend ? 'pointer' : 'default',
                fontSize: '16px',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                opacity: canSend ? 1 : 0.5,
              }}
            >
              <span>↑</span>
            </button>
          </div>
          {isStreaming && (
            <div
              style={{
                marginTop: '8px',
                fontSize: '12px',
                color: 'var(--chat-text-muted, #858585)',
              }}
            >
              Claude is responding...
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// Empty state with connection status
const EmptyState = ({ isConnected }) => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      color: 'var(--chat-text-muted, #858585)',
      textAlign: 'center',
    }}
  >
    <div style={{ fontSize: '16px', fontWeight: 500, marginBottom: '8px' }}>
      Chat Mode
    </div>
    <div style={{ fontSize: '13px', opacity: 0.7, marginBottom: '16px' }}>
      {isConnected
        ? 'Type a message to start chatting with Claude'
        : 'Connecting to server...'}
    </div>
    <div style={{ fontSize: '12px', opacity: 0.5 }}>
      Tip: Type <code style={{ background: '#333', padding: '2px 4px', borderRadius: '3px' }}>@</code> for files, <code style={{ background: '#333', padding: '2px 4px', borderRadius: '3px' }}>/</code> for commands
    </div>
  </div>
)

// File menu component
const FileMenu = ({ files, selectedIndex, onSelect }) => (
  <div style={menuStyles.container}>
    <div style={menuStyles.header}>Files</div>
    {files.map((file, index) => (
      <button
        key={file.path}
        onClick={() => onSelect(file)}
        style={{
          ...menuStyles.item,
          ...(index === selectedIndex ? menuStyles.itemSelected : {}),
        }}
      >
        <span style={menuStyles.icon}>{file.isDirectory ? '📁' : '📄'}</span>
        <span>{file.name}</span>
      </button>
    ))}
  </div>
)

// Command menu component
const CommandMenu = ({ commands, selectedIndex, onSelect }) => (
  <div style={menuStyles.container}>
    <div style={menuStyles.header}>Commands</div>
    {commands.map((cmd, index) => (
      <button
        key={cmd.id}
        onClick={() => onSelect(cmd)}
        style={{
          ...menuStyles.item,
          ...(index === selectedIndex ? menuStyles.itemSelected : {}),
        }}
      >
        <span style={{ fontFamily: 'monospace' }}>{cmd.label}</span>
        {cmd.description && (
          <span style={menuStyles.description}>{cmd.description}</span>
        )}
      </button>
    ))}
  </div>
)

// Simple user message component
const UserMessageSimple = ({ message }) => (
  <div
    style={{
      display: 'flex',
      justifyContent: 'flex-start',
      marginBottom: 'var(--chat-spacing-md, 12px)',
    }}
  >
    <div
      style={{
        backgroundColor: 'var(--chat-user-bubble, #393937)',
        color: 'var(--chat-text, #eee)',
        padding: '6px 12px',
        borderRadius: 'var(--chat-radius-md, 8px)',
        maxWidth: '85%',
        fontSize: '14px',
        lineHeight: '1.3',
        wordBreak: 'break-word',
      }}
    >
      {message.content?.[0]?.text || ''}
    </div>
  </div>
)

// Simple assistant message component
const AssistantMessageSimple = ({ message, isStreaming }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: 'var(--chat-spacing-sm, 8px)',
      marginBottom: 'var(--chat-spacing-md, 12px)',
    }}
  >
    <span
      style={{
        color: isStreaming ? '#ae5630' : '#858585',
        fontSize: '8px',
        lineHeight: '22px',
        flexShrink: 0,
        marginTop: '2px',
      }}
    >
      ●
    </span>
    <div
      style={{
        flex: 1,
        color: 'var(--chat-text, #cccccc)',
        fontSize: '14px',
        lineHeight: '1.6',
        wordBreak: 'break-word',
        whiteSpace: 'pre-wrap',
      }}
    >
      {message.content?.[0]?.text || ''}
      {isStreaming && (
        <span
          style={{
            display: 'inline-block',
            width: '2px',
            height: '16px',
            backgroundColor: 'var(--chat-text, #cccccc)',
            marginLeft: '2px',
            animation: 'blink 1s step-end infinite',
          }}
        />
      )}
    </div>
  </div>
)

// Menu styles
const menuStyles = {
  container: {
    position: 'absolute',
    bottom: '100%',
    left: '12px',
    right: '12px',
    backgroundColor: 'var(--chat-panel-bg, #252526)',
    border: '1px solid var(--chat-border, #454545)',
    borderRadius: '8px',
    maxHeight: '200px',
    overflowY: 'auto',
    marginBottom: '8px',
    zIndex: 10,
  },
  header: {
    padding: '8px 12px 4px',
    color: 'var(--chat-text-muted, #858585)',
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    width: '100%',
    padding: '8px 12px',
    backgroundColor: 'transparent',
    border: 'none',
    color: 'var(--chat-text, #cccccc)',
    fontSize: '13px',
    cursor: 'pointer',
    textAlign: 'left',
  },
  itemSelected: {
    backgroundColor: '#0078d4',
    color: 'white',
  },
  icon: {
    fontSize: '14px',
    width: '20px',
    textAlign: 'center',
  },
  description: {
    marginLeft: 'auto',
    color: 'var(--chat-text-muted, #858585)',
    fontSize: '12px',
  },
}

export default ChatView
