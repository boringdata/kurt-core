import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

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

// Status colors use CSS variables from chatThemeVars
const STATUS_COLORS = {
  running: 'var(--chat-text-muted)',   // Grey - in progress
  complete: 'var(--chat-success)',     // Green - success
  error: 'var(--chat-error)',          // Red - error
  pending: 'var(--chat-text-muted)',   // Grey - waiting
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
            fontSize: '7px',
            lineHeight: 1,
            flexShrink: 0,
            marginTop: '5px',
            marginLeft: '-8px',
            width: '8px',
            height: '8px',
            background: 'var(--chat-bg)',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            zIndex: 2,
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
                color: 'var(--chat-text)',
                fontSize: '14px',
              }}
            >
              {toolName}
            </span>
            {description && (
              <span
                style={{
                  color: 'var(--chat-text-muted)',
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
                  color: 'var(--chat-text-muted)',
                  fontSize: '12px',
                  marginLeft: 'auto',
                }}
              >
                {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </span>
            )}
          </div>

          {/* Subtitle line (e.g., "Added 20 lines") */}
          {subtitle && (
            <span
              style={{
                color: 'var(--chat-text-muted)',
                fontSize: 'var(--text-sm)',
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
            marginLeft: '16px', // Align with text after bullet (0px bullet margin + 8px bullet width + 8px gap)
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
      backgroundColor: 'var(--chat-tool-bg, var(--chat-input-bg))',
      borderRadius: 'var(--radius-md, 8px)',
      padding: 'var(--space-3, 12px) var(--space-4, 16px)',
      fontSize: 'var(--text-sm)',
      fontFamily: 'var(--font-mono)',
      color: 'var(--chat-text)',
      overflow: 'auto',
      maxHeight: '300px',
      border: '1px solid var(--chat-border)',
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
      gap: 'var(--space-2, 8px)',
      marginBottom: 'var(--space-1, 4px)',
    }}
  >
    {language && (
      <span
        style={{
          color: 'var(--chat-text-muted)',
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
        fontSize: 'var(--text-sm)',
        color: 'var(--chat-text)',
        backgroundColor: 'var(--chat-command-bg, var(--chat-input-bg))',
        padding: '4px 8px',
        borderRadius: 'var(--radius-sm, 6px)',
        border: '1px solid var(--chat-border)',
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
      color: 'var(--chat-error)',
      fontSize: 'var(--text-sm)',
      fontFamily: 'var(--font-mono)',
      padding: 'var(--chat-spacing-sm, 8px)',
      backgroundColor: 'var(--chat-error-bg)',
      borderRadius: 'var(--chat-radius-sm, 4px)',
      borderLeft: '3px solid var(--chat-error)',
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
      backgroundColor: 'var(--chat-code-bg, var(--chat-input-bg))',
      color: 'var(--chat-code-inline)',
      padding: '2px 6px',
      borderRadius: 'var(--radius-sm, 6px)',
      fontFamily: 'var(--font-mono)',
      fontSize: '0.875em',
      border: '1px solid var(--chat-border)',
    }}
  >
    {children}
  </code>
)

export default ToolUseBlock
