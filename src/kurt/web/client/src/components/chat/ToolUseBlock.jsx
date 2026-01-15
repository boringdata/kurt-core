import { useState } from 'react'

/**
 * ToolUseBlock - Wrapper component for tool use displays
 *
 * Provides consistent styling for all tool renderers:
 * - Bullet indicator (colored based on status)
 * - Tool name label
 * - Collapsible content area
 * - Status indicators (running, complete, error)
 *
 * From reference screenshots:
 * - Green bullet (●) for success
 * - Grey bullet for pending/running
 * - Red bullet for errors
 * - Tool name in bold, then description
 */

// Status colors matching VSCode Claude Code extension
const STATUS_COLORS = {
  running: '#858585',     // Grey - in progress
  complete: '#89d185',    // Green - success
  error: '#f48771',       // Red - error
  pending: '#858585',     // Grey - waiting
}

const ToolUseBlock = ({
  toolName,
  description,
  subtitle,
  status = 'complete',
  children,
  collapsible = false,
  defaultExpanded = true,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const bulletColor = STATUS_COLORS[status] || STATUS_COLORS.complete

  return (
    <div
      className={`tool-use-block ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--chat-spacing-xs, 4px)',
        marginBottom: 'var(--chat-spacing-sm, 8px)',
      }}
    >
      {/* Header row with bullet, tool name, and description */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 'var(--chat-spacing-sm, 8px)',
          cursor: collapsible ? 'pointer' : 'default',
        }}
        onClick={collapsible ? () => setIsExpanded(!isExpanded) : undefined}
      >
        {/* Status bullet */}
        <span
          style={{
            color: bulletColor,
            fontSize: '8px',
            lineHeight: '22px',
            flexShrink: 0,
            marginTop: '2px',
          }}
        >
          ●
        </span>

        {/* Tool name, description, and subtitle */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
          }}
        >
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'baseline',
              gap: '6px',
            }}
          >
            <span
              style={{
                fontWeight: 600,
                color: 'var(--chat-text, #cccccc)',
                fontSize: '14px',
              }}
            >
              {toolName}
            </span>
            {description && (
              <span
                style={{
                  color: 'var(--chat-text-muted, #858585)',
                  fontSize: '14px',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {description}
              </span>
            )}

            {/* Collapse indicator */}
            {collapsible && (
              <span
                style={{
                  color: 'var(--chat-text-muted, #858585)',
                  fontSize: '12px',
                  marginLeft: 'auto',
                }}
              >
                {isExpanded ? '▼' : '▶'}
              </span>
            )}
          </div>

          {/* Subtitle line (e.g., "Added 20 lines") */}
          {subtitle && (
            <span
              style={{
                color: 'var(--chat-text-muted, #858585)',
                fontSize: '13px',
                marginTop: '2px',
              }}
            >
              {subtitle}
            </span>
          )}
        </div>
      </div>

      {/* Content area (collapsible) */}
      {(!collapsible || isExpanded) && children && (
        <div
          style={{
            marginLeft: '16px', // Align with text after bullet
            paddingLeft: 'var(--chat-spacing-sm, 8px)',
          }}
        >
          {children}
        </div>
      )}
    </div>
  )
}

/**
 * ToolOutput - Styled container for tool output/results
 */
export const ToolOutput = ({ children, style = {}, className = '' }) => (
  <div
    className={className}
    style={{
      backgroundColor: 'var(--chat-input-bg, #3c3c3c)',
      borderRadius: 'var(--chat-radius-sm, 4px)',
      padding: 'var(--chat-spacing-sm, 8px) var(--chat-spacing-md, 12px)',
      fontSize: '13px',
      fontFamily: 'var(--font-mono)',
      color: 'var(--chat-text, #cccccc)',
      overflow: 'auto',
      maxHeight: '300px',
      ...style,
    }}
  >
    {children}
  </div>
)

/**
 * ToolCommand - Styled command/input display
 */
export const ToolCommand = ({ command, language }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--chat-spacing-sm, 8px)',
      marginBottom: 'var(--chat-spacing-xs, 4px)',
    }}
  >
    {language && (
      <span
        style={{
          color: 'var(--chat-text-muted, #858585)',
          fontSize: '11px',
          textTransform: 'lowercase',
        }}
      >
        {language}
      </span>
    )}
    <code
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '13px',
        color: 'var(--chat-text, #cccccc)',
        backgroundColor: 'var(--chat-input-bg, #3c3c3c)',
        padding: '2px 6px',
        borderRadius: '3px',
      }}
    >
      {command}
    </code>
  </div>
)

/**
 * ToolError - Styled error message display
 */
export const ToolError = ({ message }) => (
  <div
    style={{
      color: 'var(--chat-error, #f48771)',
      fontSize: '13px',
      fontFamily: 'var(--font-mono)',
      padding: 'var(--chat-spacing-sm, 8px)',
      backgroundColor: 'rgba(244, 135, 113, 0.1)',
      borderRadius: 'var(--chat-radius-sm, 4px)',
      borderLeft: '3px solid var(--chat-error, #f48771)',
    }}
  >
    {message}
  </div>
)

/**
 * InlineCode - Styled inline code element
 */
export const InlineCode = ({ children }) => (
  <code
    style={{
      backgroundColor: 'var(--chat-input-bg, #3c3c3c)',
      color: '#e6b450', // Yellow/gold for inline code
      padding: '2px 6px',
      borderRadius: '3px',
      fontFamily: 'var(--font-mono)',
      fontSize: '13px',
    }}
  >
    {children}
  </code>
)

export default ToolUseBlock
