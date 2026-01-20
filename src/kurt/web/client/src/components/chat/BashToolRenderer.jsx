import ToolUseBlock, { ToolOutput, ToolError, ToolCommand } from './ToolUseBlock'

/**
 * BashToolRenderer - Displays bash command executions
 *
 * From reference screenshots:
 * - Header: "Bash DESCRIPTION" with command description
 * - Command line in mono font
 * - Output section showing terminal output
 * - Collapsible for long outputs
 * - Error state for failed commands
 */

const BashToolRenderer = ({
  command,
  description,
  output,
  exitCode,
  error,
  status = 'complete',
  compact = false,
}) => {
  const formatOutput = (text) => {
    if (!text) return ''
    const lines = text.split('\n')
    const maxLines = 8
    if (lines.length <= maxLines) return text
    const shown = lines.slice(0, maxLines).join('\n')
    const remaining = lines.length - maxLines
    return `${shown}\n... +${remaining} lines`
  }

  // Determine status based on exit code if not provided
  const hasExitCode = typeof exitCode === 'number'
  const effectiveStatus = error ? 'error' : hasExitCode && exitCode !== 0 ? 'error' : status
  const isStreaming = ['pending', 'running', 'streaming'].includes(effectiveStatus)

  return (
    <ToolUseBlock
      toolName="Bash"
      description={description || (command?.length > 60 ? command.slice(0, 60) + '...' : command)}
      status={effectiveStatus}
      collapsible={output && output.length > 300}
      defaultExpanded={true}
    >
      {/* Command display */}
      {command && !compact && (
        <div
          style={{
            marginBottom: 'var(--chat-spacing-sm, 8px)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: 'var(--chat-text-muted)',
              fontSize: '12px',
              marginBottom: '4px',
            }}
          >
            <span>$</span>
          </div>
          <code
            style={{
              display: 'block',
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              color: 'var(--chat-text)',
              backgroundColor: 'var(--chat-input-bg)',
              padding: '8px 12px',
              borderRadius: 'var(--chat-radius-sm, 4px)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {command}
          </code>
        </div>
      )}

      {/* Error display */}
      {error && <ToolError message={error} />}

      {/* Output display */}
      {output && !error && compact && (
        <pre className="claude-bash-compact">
          {(() => {
            const rawLines = output.split('\n')
            const maxLines = 3
            const shown = rawLines.slice(0, maxLines)
            const formatted = shown.map((line, idx) =>
              `${idx === 0 ? '└' : ' '} ${line}`.trimEnd()
            )
            if (rawLines.length > maxLines) {
              formatted.push(`  ... +${rawLines.length - maxLines} lines`)
            }
            return formatted.join('\n')
          })()}
          {isStreaming && <span className="claude-streaming-cursor" aria-hidden="true">▌</span>}
        </pre>
      )}

      {output && !error && !compact && (
        <ToolOutput
          className="claude-tool-output"
          streaming={isStreaming}
          style={{
            maxHeight: '260px',
          }}
        >
          <pre
            style={{
              margin: 0,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              lineHeight: '1.4',
            }}
          >
            {formatOutput(output)}
          </pre>
        </ToolOutput>
      )}

      {/* Exit code indicator for non-zero */}
      {exitCode !== undefined && exitCode !== 0 && !error && (
        <div
          style={{
            marginTop: 'var(--chat-spacing-xs, 4px)',
            fontSize: '12px',
            color: 'var(--chat-error)',
          }}
        >
          Exit code: {exitCode}
        </div>
      )}

      {/* Pending state */}
      {status === 'pending' && !output && (
        <div
          style={{
            color: 'var(--chat-text-muted)',
            fontSize: '13px',
            fontStyle: 'italic',
          }}
        >
          Waiting for permission...
        </div>
      )}

      {/* Running state */}
      {status === 'running' && !output && (
        <div
          style={{
            color: 'var(--chat-text-muted)',
            fontSize: '13px',
            fontStyle: 'italic',
          }}
        >
          Running command...
        </div>
      )}
    </ToolUseBlock>
  )
}

export default BashToolRenderer
