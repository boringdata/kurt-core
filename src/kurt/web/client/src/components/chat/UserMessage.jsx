import { MessagePrimitive } from '@assistant-ui/react'
import { forwardRef } from 'react'

/**
 * UserMessage - Displays user messages
 *
 * From reference screenshots:
 * - User messages have rounded bubble with darker background
 * - Text is white/light
 * - Bubble has subtle border radius
 * - Left-aligned with indent
 */

const UserMessage = forwardRef(({ className = '', contextFile, ...props }, ref) => {
  return (
    <MessagePrimitive.Root
      ref={ref}
      className={`user-message ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        marginBottom: 'var(--chat-spacing-md, 12px)',
      }}
      {...props}
    >
      <UserMessageBubble />
      {contextFile && <ContextLabel file={contextFile} />}
      <UserMessageAttachments />
    </MessagePrimitive.Root>
  )
})

UserMessage.displayName = 'UserMessage'

/**
 * Context label shown below user message bubble
 * Shows the file that was used as context (e.g., "PROMPTS.md")
 */
const ContextLabel = ({ file }) => {
  return (
    <div
      style={{
        marginTop: '4px',
        fontSize: '12px',
        color: 'var(--chat-text-muted, #858585)',
        fontFamily: 'var(--font-mono, monospace)',
      }}
    >
      {file}
    </div>
  )
}

/**
 * User message bubble with text content
 */
const UserMessageBubble = () => {
  return (
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
      <MessagePrimitive.Content />
    </div>
  )
}

/**
 * User message attachments (files, images)
 */
const UserMessageAttachments = () => {
  return (
    <MessagePrimitive.Attachments
      components={{
        File: FileAttachment,
        Image: ImageAttachment,
      }}
    />
  )
}

/**
 * File attachment display
 */
const FileAttachment = ({ file }) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginTop: '8px',
        padding: '8px 12px',
        backgroundColor: 'var(--chat-panel-bg, #252526)',
        border: '1px solid var(--chat-border, #454545)',
        borderRadius: 'var(--chat-radius-sm, 4px)',
        fontSize: '12px',
        color: 'var(--chat-text-muted, #858585)',
      }}
    >
      <span style={{ fontSize: '14px' }}>📎</span>
      <span>{file?.name || 'File'}</span>
    </div>
  )
}

/**
 * Image attachment display
 */
const ImageAttachment = ({ image }) => {
  return (
    <div
      style={{
        marginTop: '8px',
        borderRadius: 'var(--chat-radius-sm, 4px)',
        overflow: 'hidden',
        maxWidth: '300px',
      }}
    >
      <img
        src={image?.url}
        alt={image?.name || 'Attached image'}
        style={{
          width: '100%',
          height: 'auto',
          display: 'block',
        }}
      />
    </div>
  )
}

export default UserMessage
