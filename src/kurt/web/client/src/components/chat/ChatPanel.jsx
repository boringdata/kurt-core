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
        backgroundColor: 'var(--chat-bg)',
        color: 'var(--chat-text)',
        fontFamily: 'var(--font-family)',
        fontSize: 'var(--text-sm)',
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

// CSS Variables for theming - maps chat tokens to main design tokens
export const chatThemeVars = `
  :root {
    /* Chat theme - maps to main design tokens */
    --chat-bg: var(--color-bg-secondary);
    --chat-panel-bg: var(--color-bg-primary);
    --chat-input-bg: var(--color-bg-tertiary);
    --chat-code-bg: var(--color-code-bg);
    --chat-tool-bg: var(--color-tool-bg);
    --chat-command-bg: var(--color-command-bg);
    --chat-text: var(--color-text-primary);
    --chat-text-muted: var(--color-text-secondary);
    --chat-text-tertiary: var(--color-text-tertiary);
    --chat-accent: var(--color-accent);
    --chat-success: var(--color-success);
    --chat-success-bg: var(--color-success-light);
    --chat-error: var(--color-error);
    --chat-error-bg: var(--color-error-light);
    --chat-warning: var(--color-warning);
    --chat-info: var(--color-info);
    --chat-border: var(--color-border);
    --chat-user-bubble: var(--color-bg-tertiary);
    --chat-code-inline: var(--color-accent);
    --chat-diff-add-bg: var(--color-diff-add-bg);
    --chat-diff-add-text: var(--color-diff-add-text);
    --chat-diff-remove-bg: var(--color-diff-remove-bg);
    --chat-diff-remove-text: var(--color-diff-remove-text);
    --chat-spacing-xs: var(--space-1);
    --chat-spacing-sm: var(--space-2);
    --chat-spacing-md: var(--space-3);
    --chat-spacing-lg: var(--space-4);
    --chat-spacing-xl: var(--space-6);
    --chat-radius-sm: var(--radius-sm);
    --chat-radius-md: var(--radius-md);
    --chat-radius-lg: var(--radius-lg);
    --font-family: var(--font-sans);
    --font-mono: var(--font-mono);
  }
`

export default ChatPanel
