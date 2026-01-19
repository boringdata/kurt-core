import { ThreadPrimitive } from '@assistant-ui/react'
import { forwardRef } from 'react'

/**
 * ChatPanel - Main container for the chat interface
 * Extends ThreadPrimitive.Root for assistant-ui integration
 *
 * VSCode Claude Code Extension dark theme:
 * - Background: #1e1e1e
 * - Panel bg: #252526
 * - Text: #cccccc
 * - Muted: #858585
 * - Accent: #0078d4
 */

const ChatPanel = forwardRef(({ children, className = '', ...props }, ref) => {
  return (
    <ThreadPrimitive.Root
      ref={ref}
      className={`chat-panel ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        backgroundColor: 'var(--chat-bg, #1e1e1e)',
        color: 'var(--chat-text, #cccccc)',
        fontFamily: 'var(--font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif)',
        fontSize: '13px',
        lineHeight: '1.5',
        overflow: 'hidden',
      }}
      {...props}
    >
      {children}
    </ThreadPrimitive.Root>
  )
})

ChatPanel.displayName = 'ChatPanel'

// CSS Variables for theming
export const chatThemeVars = `
  :root {
    /* VSCode-style dark theme */
    --chat-bg: #1e1e1e;
    --chat-panel-bg: #252526;
    --chat-input-bg: #3c3c3c;
    --chat-text: #cccccc;
    --chat-text-muted: #858585;
    --chat-accent: #0078d4;
    --chat-success: #89d185;
    --chat-error: #f48771;
    --chat-warning: #cca700;
    --chat-border: #454545;
    --chat-user-bubble: #393937;
    --chat-spacing-xs: 4px;
    --chat-spacing-sm: 8px;
    --chat-spacing-md: 12px;
    --chat-spacing-lg: 16px;
    --chat-spacing-xl: 24px;
    --chat-radius-sm: 4px;
    --chat-radius-md: 8px;
    --chat-radius-lg: 12px;
    --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --font-mono: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace;
  }
`

export default ChatPanel
