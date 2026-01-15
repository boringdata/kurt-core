import { useState, useRef, useEffect, useCallback } from 'react'
import { ComposerPrimitive, useComposer } from '@assistant-ui/react'

/**
 * InputArea - Rich input with @ file picker and / command menu
 * Uses ComposerPrimitive from assistant-ui for core functionality
 *
 * From reference screenshots:
 * - Text input with auto-resize
 * - @ triggers file picker menu
 * - / triggers command menu with grouped sections
 * - Bottom toolbar: Ask before edits, context file, attachment, send
 */

const InputArea = ({
  onFileSelect,
  onCommandSelect,
  files = [],
  commands = [],
  contextFile,
  askBeforeEdits = true,
  onToggleAskBeforeEdits,
  placeholder = 'Type a message...',
}) => {
  const [showAtMenu, setShowAtMenu] = useState(false)
  const [showSlashMenu, setShowSlashMenu] = useState(false)
  const [menuFilter, setMenuFilter] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [lastText, setLastText] = useState('')
  const inputRef = useRef(null)

  // Get composer state from assistant-ui
  const composer = useComposer()

  // Handle input changes for menu triggers - watch composer text
  useEffect(() => {
    const currentText = composer?.text || ''
    if (currentText === lastText) return

    const lastChar = currentText.slice(-1)
    const prevChar = currentText.slice(-2, -1)

    if (lastChar === '@' && (prevChar === '' || prevChar === ' ')) {
      setShowAtMenu(true)
      setShowSlashMenu(false)
      setMenuFilter('')
      setSelectedIndex(0)
    } else if (lastChar === '/' && (prevChar === '' || prevChar === ' ')) {
      setShowSlashMenu(true)
      setShowAtMenu(false)
      setMenuFilter('')
      setSelectedIndex(0)
    } else if (showAtMenu || showSlashMenu) {
      // Update filter based on text after trigger
      const triggerChar = showAtMenu ? '@' : '/'
      const lastTriggerIndex = currentText.lastIndexOf(triggerChar)
      if (lastTriggerIndex >= 0) {
        setMenuFilter(currentText.slice(lastTriggerIndex + 1))
      }
    }

    setLastText(currentText)
  }, [composer?.text, lastText, showAtMenu, showSlashMenu])

  // Handle key events for menu navigation
  const handleKeyDown = (e) => {
    if (showAtMenu || showSlashMenu) {
      const items = showAtMenu ? filteredFiles : flattenedCommands
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => Math.min(prev + 1, items.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => Math.max(prev - 1, 0))
      } else if (e.key === 'Enter' && items.length > 0) {
        e.preventDefault()
        handleMenuSelect(items[selectedIndex])
      } else if (e.key === 'Escape') {
        setShowAtMenu(false)
        setShowSlashMenu(false)
      }
    }
  }

  const handleMenuSelect = (item) => {
    if (showAtMenu) {
      onFileSelect?.(item)
    } else {
      onCommandSelect?.(item)
    }
    setShowAtMenu(false)
    setShowSlashMenu(false)
    // Remove the trigger text from composer
    const currentText = composer?.text || ''
    const triggerChar = showAtMenu ? '@' : '/'
    const lastIndex = currentText.lastIndexOf(triggerChar)
    if (lastIndex >= 0 && composer?.setText) {
      composer.setText(currentText.slice(0, lastIndex))
    }
  }

  // Filter files based on menu filter
  const filteredFiles = files.filter((f) =>
    f.name.toLowerCase().includes(menuFilter.toLowerCase())
  )

  // Flatten commands for navigation while keeping groups for display
  const flattenedCommands = commands.flatMap((group) => group.items || [])

  return (
    <ComposerPrimitive.Root style={styles.container}>
      {/* @ File Menu */}
      {showAtMenu && filteredFiles.length > 0 && (
        <FileMenu
          files={filteredFiles}
          selectedIndex={selectedIndex}
          onSelect={handleMenuSelect}
        />
      )}

      {/* / Command Menu */}
      {showSlashMenu && commands.length > 0 && (
        <CommandMenu
          groups={commands}
          selectedIndex={selectedIndex}
          flattenedCommands={flattenedCommands}
          onSelect={handleMenuSelect}
        />
      )}

      {/* Input area using ComposerPrimitive.Input */}
      <div style={styles.inputWrapper}>
        <ComposerPrimitive.Input
          ref={inputRef}
          placeholder={placeholder}
          rows={1}
          maxRows={8}
          autoFocus
          onKeyDown={handleKeyDown}
          style={styles.inputStyle}
        />
      </div>

      {/* Toolbar */}
      <div style={styles.toolbar}>
        <div style={styles.toolbarLeft}>
          {/* Ask before edits toggle */}
          <button
            onClick={onToggleAskBeforeEdits}
            style={{
              ...styles.toolbarButton,
              opacity: askBeforeEdits ? 1 : 0.5,
            }}
            type="button"
          >
            <span style={styles.pencilIcon}>✏️</span>
            <span>Ask before edits</span>
          </button>

          {/* Context file */}
          {contextFile && (
            <div style={styles.contextFile}>
              <span style={styles.codeIcon}>&lt;/&gt;</span>
              <span>{contextFile}</span>
            </div>
          )}
        </div>

        <div style={styles.toolbarRight}>
          {/* Attachment button */}
          <button style={styles.iconButton} title="Attach file" type="button">
            📎
          </button>

          {/* Slash command button */}
          <button
            style={styles.iconButton}
            onClick={() => {
              setShowSlashMenu(!showSlashMenu)
              setShowAtMenu(false)
            }}
            title="Commands"
            type="button"
          >
            /
          </button>

          {/* Send button using ComposerPrimitive.Send */}
          <ComposerPrimitive.Send style={styles.sendButton}>
            ↑
          </ComposerPrimitive.Send>
        </div>
      </div>
    </ComposerPrimitive.Root>
  )
}

/**
 * FileMenu - @ file picker menu
 */
const FileMenu = ({ files, selectedIndex, onSelect }) => (
  <div style={styles.menu}>
    {files.map((file, index) => (
      <button
        key={file.path || file.name}
        onClick={() => onSelect(file)}
        style={{
          ...styles.menuItem,
          ...(index === selectedIndex ? styles.menuItemSelected : {}),
        }}
      >
        <span style={styles.fileIcon}>{file.isDirectory ? '📁' : '📄'}</span>
        <span>{file.name}</span>
      </button>
    ))}
  </div>
)

/**
 * CommandMenu - / command menu with groups
 */
const CommandMenu = ({ groups, selectedIndex, flattenedCommands, onSelect }) => {
  let currentIndex = 0

  return (
    <div style={styles.menu}>
      {groups.map((group) => (
        <div key={group.label}>
          <div style={styles.menuGroupLabel}>{group.label}</div>
          {group.items?.map((item) => {
            const itemIndex = currentIndex++
            return (
              <button
                key={item.id || item.label}
                onClick={() => onSelect(item)}
                style={{
                  ...styles.menuItem,
                  ...(itemIndex === selectedIndex ? styles.menuItemSelected : {}),
                }}
              >
                <span>{item.label}</span>
                {item.value && <span style={styles.menuItemValue}>{item.value}</span>}
                {item.toggle !== undefined && (
                  <span style={styles.toggle}>
                    {item.toggle ? '●' : '○'}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      ))}
    </div>
  )
}

const styles = {
  container: {
    padding: 'var(--chat-spacing-md, 12px)',
    borderTop: '1px solid var(--chat-border, #454545)',
    position: 'relative',
  },
  inputWrapper: {
    backgroundColor: 'var(--chat-input-bg, #3c3c3c)',
    borderRadius: 'var(--chat-radius-md, 8px)',
    padding: '8px 12px',
  },
  inputStyle: {
    width: '100%',
    backgroundColor: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'var(--chat-text, #cccccc)',
    fontSize: '14px',
    fontFamily: 'inherit',
    resize: 'none',
    boxSizing: 'border-box',
  },
  toolbar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '8px',
    padding: '0 4px',
  },
  toolbarLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  toolbarRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  toolbarButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 8px',
    backgroundColor: 'transparent',
    border: 'none',
    color: 'var(--chat-text-muted, #858585)',
    fontSize: '12px',
    cursor: 'pointer',
  },
  pencilIcon: {
    fontSize: '12px',
  },
  contextFile: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    color: 'var(--chat-text-muted, #858585)',
    fontSize: '12px',
  },
  codeIcon: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
  },
  iconButton: {
    width: '28px',
    height: '28px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
    border: 'none',
    color: 'var(--chat-text-muted, #858585)',
    fontSize: '14px',
    cursor: 'pointer',
    borderRadius: '4px',
  },
  sendButton: {
    width: '32px',
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#ae5630',
    border: 'none',
    color: 'white',
    fontSize: '16px',
    fontWeight: 'bold',
    cursor: 'pointer',
    borderRadius: '6px',
  },
  menu: {
    position: 'absolute',
    bottom: '100%',
    left: 'var(--chat-spacing-md, 12px)',
    right: 'var(--chat-spacing-md, 12px)',
    backgroundColor: 'var(--chat-panel-bg, #252526)',
    border: '1px solid var(--chat-border, #454545)',
    borderRadius: 'var(--chat-radius-md, 8px)',
    maxHeight: '300px',
    overflowY: 'auto',
    marginBottom: '8px',
  },
  menuItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    width: '100%',
    padding: '8px 12px',
    backgroundColor: 'transparent',
    border: 'none',
    color: 'var(--chat-text, #cccccc)',
    fontSize: '14px',
    cursor: 'pointer',
    textAlign: 'left',
  },
  menuItemSelected: {
    backgroundColor: 'var(--chat-accent, #0078d4)',
    color: 'white',
  },
  menuItemValue: {
    marginLeft: 'auto',
    color: 'var(--chat-text-muted, #858585)',
    fontSize: '13px',
  },
  menuGroupLabel: {
    padding: '8px 12px 4px',
    color: 'var(--chat-text-muted, #858585)',
    fontSize: '12px',
    fontWeight: 500,
  },
  fileIcon: {
    fontSize: '14px',
  },
  toggle: {
    marginLeft: 'auto',
    fontSize: '12px',
    color: 'var(--chat-text-muted, #858585)',
  },
}

export default InputArea
