import ToolUseBlock, { ToolError } from './ToolUseBlock'

/**
 * EditToolRenderer - Displays file edit operations with diff view
 *
 * From reference screenshots:
 * - Header: "Edit FILENAME" + "Added X lines" / "Removed X lines"
 * - Diff display with green (additions) and red (deletions)
 * - Line-by-line diff with +/- prefixes
 */

const EditToolRenderer = ({
  filePath,
  oldContent,
  newContent,
  diff,
  linesAdded = 0,
  linesRemoved = 0,
  error,
  status = 'complete',
}) => {
  const fileName = filePath?.split('/').pop() || filePath

  // Build subtitle from line changes
  const changes = []
  if (linesAdded > 0) changes.push(`Added ${linesAdded} line${linesAdded > 1 ? 's' : ''}`)
  if (linesRemoved > 0) changes.push(`Removed ${linesRemoved} line${linesRemoved > 1 ? 's' : ''}`)
  const subtitle = changes.join(', ')

  // Parse diff lines if provided as string
  const diffLines = typeof diff === 'string' ? diff.split('\n') : diff || []

  return (
    <ToolUseBlock
      toolName="Edit"
      description={fileName}
      subtitle={subtitle}
      status={status}
      collapsible={diffLines.length > 20}
      defaultExpanded={true}
    >
      {error ? (
        <ToolError message={error} />
      ) : diffLines.length > 0 ? (
        <DiffView lines={diffLines} />
      ) : oldContent && newContent ? (
        <SimpleDiff oldContent={oldContent} newContent={newContent} />
      ) : status === 'pending' ? (
        <div
          style={{
            color: 'var(--chat-text-muted, #858585)',
            fontSize: '13px',
            fontStyle: 'italic',
          }}
        >
          Waiting for permission...
        </div>
      ) : status === 'running' ? (
        <div
          style={{
            color: 'var(--chat-text-muted, #858585)',
            fontSize: '13px',
            fontStyle: 'italic',
          }}
        >
          Editing file
          <span className="claude-waiting-dots" aria-hidden="true">
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </span>
        </div>
      ) : null}
    </ToolUseBlock>
  )
}

/**
 * DiffView - Renders unified diff with syntax highlighting
 */
const DiffView = ({ lines }) => (
  <div
    style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '13px',
      lineHeight: '1.5',
      borderRadius: 'var(--chat-radius-sm, 4px)',
      overflow: 'hidden',
    }}
  >
    {lines.map((line, i) => {
      const isAddition = line.startsWith('+') && !line.startsWith('+++')
      const isDeletion = line.startsWith('-') && !line.startsWith('---')
      const isHeader = line.startsWith('@@') || line.startsWith('---') || line.startsWith('+++')

      let bgColor = 'transparent'
      let textColor = 'var(--chat-text, #cccccc)'

      if (isAddition) {
        bgColor = 'rgba(137, 209, 133, 0.2)'
        textColor = '#89d185'
      } else if (isDeletion) {
        bgColor = 'rgba(244, 135, 113, 0.2)'
        textColor = '#f48771'
      } else if (isHeader) {
        textColor = 'var(--chat-text-muted, #858585)'
      }

      return (
        <div
          key={i}
          style={{
            backgroundColor: bgColor,
            padding: '0 8px',
            color: textColor,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {line || ' '}
        </div>
      )
    })}
  </div>
)

/**
 * SimpleDiff - Basic before/after diff when no unified diff provided
 */
const SimpleDiff = ({ oldContent, newContent }) => {
  const oldLines = oldContent.split('\n')
  const newLines = newContent.split('\n')

  return (
    <div
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '13px',
        lineHeight: '1.5',
        borderRadius: 'var(--chat-radius-sm, 4px)',
        overflow: 'hidden',
      }}
    >
      {/* Show removed lines */}
      {oldLines.map((line, i) => (
        <div
          key={`old-${i}`}
          style={{
            backgroundColor: 'rgba(244, 135, 113, 0.2)',
            padding: '0 8px',
            color: '#f48771',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          -{line || ' '}
        </div>
      ))}
      {/* Show added lines */}
      {newLines.map((line, i) => (
        <div
          key={`new-${i}`}
          style={{
            backgroundColor: 'rgba(137, 209, 133, 0.2)',
            padding: '0 8px',
            color: '#89d185',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          +{line || ' '}
        </div>
      ))}
    </div>
  )
}

export default EditToolRenderer
