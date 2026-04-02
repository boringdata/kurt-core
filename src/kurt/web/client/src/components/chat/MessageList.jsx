import { ThreadPrimitive } from '@assistant-ui/react'
import { forwardRef } from 'react'

/**
 * MessageList - Scrollable container for messages
 * Extends ThreadPrimitive.Viewport with auto-scroll anchoring
 */

const MessageList = forwardRef(({ children, className = '', ...props }, ref) => {
  return (
    <ThreadPrimitive.Viewport
      ref={ref}
      className={`message-list ${className}`}
      style={{
        flex: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
        padding: 'var(--chat-spacing-lg, 16px)',
        scrollBehavior: 'smooth',
      }}
      autoScroll={true}
      {...props}
    >
      {children}
    </ThreadPrimitive.Viewport>
  )
})

MessageList.displayName = 'MessageList'

/**
 * EmptyState - Shown when thread has no messages
 */
export const EmptyState = ({ children }) => {
  return (
    <ThreadPrimitive.Empty
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: 'var(--chat-text-muted)',
        padding: 'var(--chat-spacing-xl, 24px)',
        textAlign: 'center',
      }}
    >
      {children || (
        <>
          <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.5 }}>
            ✨
          </div>
          <div style={{ fontSize: '16px', fontWeight: 500, marginBottom: '8px' }}>
            Start a conversation
          </div>
          <div style={{ fontSize: 'var(--text-sm)', opacity: 0.7 }}>
            Type a message to begin
          </div>
        </>
      )}
    </ThreadPrimitive.Empty>
  )
}

/**
 * Messages - Renders the list of messages with provided components
 * Let assistant-ui handle scrolling and layout naturally
 */
export const Messages = ({ components }) => {
  return (
    <ThreadPrimitive.Messages
      components={components}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--chat-spacing-md, 12px)',
      }}
    />
  )
}

/**
 * ScrollToBottom - Button to scroll viewport to bottom
 */
export const ScrollToBottom = ({ children }) => {
  return (
    <ThreadPrimitive.ScrollToBottom
      style={{
        position: 'absolute',
        bottom: '100px',
        left: '50%',
        transform: 'translateX(-50%)',
        backgroundColor: 'var(--chat-panel-bg)',
        border: '1px solid var(--chat-border)',
        borderRadius: '20px',
        padding: '8px 16px',
        cursor: 'pointer',
        fontSize: '12px',
        color: 'var(--chat-text)',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        boxShadow: 'var(--shadow-md)',
        transition: 'opacity 0.2s ease',
      }}
    >
      {children || (
        <>
          <span>↓</span>
          <span>Scroll to bottom</span>
        </>
      )}
    </ThreadPrimitive.ScrollToBottom>
  )
}

export default MessageList
