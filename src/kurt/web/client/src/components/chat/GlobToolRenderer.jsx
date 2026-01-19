import ToolUseBlock, { ToolError, InlineCode } from './ToolUseBlock'

/**
 * GlobToolRenderer - Displays file glob/search operations
 *
 * From reference screenshots:
 * - Header: "Glob" + pattern (e.g. glob patterns)
 * - Result: "No files found" or list of matching files
 * - Collapsible file list for many results
 */

/**
 * Get icon based on file extension
 */
const getFileIcon = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()

  const icons = {
    js: '📄',
    jsx: '⚛️',
    ts: '📘',
    tsx: '⚛️',
    py: '🐍',
    md: '📝',
    json: '📋',
    css: '🎨',
    html: '🌐',
    default: '📄',
  }

  return icons[ext] || icons.default
}

const GlobToolRenderer = ({
  pattern,
  files = [],
  error,
  status = 'complete',
}) => {
  const description = (
    <>
      pattern: <InlineCode>{pattern}</InlineCode>
    </>
  )

  const fileCount = files.length
  const hasResults = fileCount > 0

  return (
    <ToolUseBlock
      toolName="Glob"
      description={description}
      status={status}
      collapsible={fileCount > 10}
      defaultExpanded={fileCount <= 20}
    >
      {error ? (
        <ToolError message={error} />
      ) : status === 'running' ? (
        <div
          style={{
            color: 'var(--chat-text-muted, #858585)',
            fontSize: '13px',
            fontStyle: 'italic',
          }}
        >
          Searching files...
        </div>
      ) : hasResults ? (
        <FileList files={files} />
      ) : (
        <div
          style={{
            color: 'var(--chat-text-muted, #858585)',
            fontSize: '13px',
          }}
        >
          No files found
        </div>
      )}
    </ToolUseBlock>
  )
}

/**
 * FileList - Renders list of files with icons
 */
const FileList = ({ files }) => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '2px',
    }}
  >
    {files.map((file, i) => (
      <div
        key={i}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '13px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--chat-text, #cccccc)',
          padding: '2px 0',
        }}
      >
        <span style={{ color: 'var(--chat-text-muted, #858585)', fontSize: '12px' }}>
          {getFileIcon(file)}
        </span>
        <span>{file}</span>
      </div>
    ))}
  </div>
)

export default GlobToolRenderer
