import ToolUseBlock, { ToolOutput, ToolError } from './ToolUseBlock'

/**
 * WriteToolRenderer - Displays file write operations
 *
 * From reference screenshots:
 * - Header: "Write FILENAME"
 * - Shows file content that will be written
 * - Permission dialog for approval (handled by PermissionPanel)
 */

const WriteToolRenderer = ({
  filePath,
  content,
  error,
  status = 'complete',
  lineCount,
}) => {
  const fileName = filePath?.split('/').pop() || filePath
  const lines = lineCount || (content ? content.split('\n').length : 0)
  const subtitle = lines > 0 ? `${lines} line${lines !== 1 ? 's' : ''}` : null

  return (
    <ToolUseBlock
      toolName="Write"
      description={fileName}
      subtitle={subtitle}
      status={status}
      collapsible={content && content.length > 500}
      defaultExpanded={true}
    >
      {error ? (
        <ToolError message={error} />
      ) : content ? (
        <ToolOutput>
          <pre
            style={{
              margin: 0,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              lineHeight: '1.5',
            }}
          >
            {content}
          </pre>
        </ToolOutput>
      ) : status === 'running' ? (
        <div
          style={{
            color: 'var(--chat-text-muted, #858585)',
            fontSize: '13px',
            fontStyle: 'italic',
          }}
        >
          Writing file...
        </div>
      ) : null}
    </ToolUseBlock>
  )
}

export default WriteToolRenderer
