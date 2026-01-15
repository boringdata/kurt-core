import { MessagePrimitive, useMessage } from '@assistant-ui/react'
import { forwardRef } from 'react'

/**
 * AssistantMessage - Displays assistant messages
 *
 * From reference screenshots:
 * - Assistant messages start with a colored bullet (●)
 * - No bubble, just text on dark background
 * - Contains text blocks, tool calls, code blocks
 * - Shows loading/streaming state with "Brewing..." text
 */

const AssistantMessage = forwardRef(({ className = '', ...props }, ref) => {
  return (
    <MessagePrimitive.Root
      ref={ref}
      className={`assistant-message ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        marginBottom: 'var(--chat-spacing-md, 12px)',
      }}
      {...props}
    >
      <AssistantMessageContent />
    </MessagePrimitive.Root>
  )
})

AssistantMessage.displayName = 'AssistantMessage'

/**
 * Assistant message content with bullet indicator
 */
const AssistantMessageContent = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--chat-spacing-sm, 8px)',
      }}
    >
      <MessagePrimitive.Content
        components={{
          Text: TextPart,
          // Tool calls will be rendered via tools.by_name in the Thread setup
        }}
      />
    </div>
  )
}

/**
 * Text part with bullet indicator
 */
const TextPart = ({ text, status }) => {
  const isStreaming = status?.type === 'running'

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 'var(--chat-spacing-sm, 8px)',
      }}
    >
      {/* Bullet indicator - gray for completed responses */}
      <span
        style={{
          color: '#858585',
          fontSize: '8px',
          lineHeight: '22px',
          flexShrink: 0,
          marginTop: '2px',
        }}
      >
        ●
      </span>

      {/* Text content */}
      <div
        style={{
          flex: 1,
          color: 'var(--chat-text, #cccccc)',
          fontSize: '14px',
          lineHeight: '1.6',
          wordBreak: 'break-word',
        }}
      >
        {text}
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
}

/**
 * Loading state - "Brewing..." indicator
 */
export const AssistantLoading = () => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--chat-spacing-sm, 8px)',
        color: 'var(--chat-text, #cccccc)',
        fontSize: '14px',
        padding: 'var(--chat-spacing-sm, 8px) 0',
      }}
    >
      <span
        style={{
          color: '#ae5630', // Orange accent from Claude Code
          fontSize: '14px',
        }}
      >
        ✳
      </span>
      <span style={{ fontStyle: 'italic' }}>Brewing...</span>
    </div>
  )
}

/**
 * Interrupted state
 */
export const AssistantInterrupted = () => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--chat-spacing-sm, 8px)',
        color: 'var(--chat-text-muted, #858585)',
        fontSize: '14px',
        fontStyle: 'italic',
        padding: 'var(--chat-spacing-sm, 8px) 0',
      }}
    >
      Interrupted
    </div>
  )
}

/**
 * CSS for blinking cursor animation
 */
export const assistantMessageStyles = `
  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }
`

export default AssistantMessage
