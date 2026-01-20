import { FileText, FileCode, FileJson, FileType } from 'lucide-react'
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
 * Get icon component based on file extension
 */
const FILE_ICONS = {
  js: FileCode,
  jsx: FileCode,
  ts: FileCode,
  tsx: FileCode,
  py: FileCode,
  md: FileType,
  json: FileJson,
  css: FileCode,
  html: FileCode,
  default: FileText,
}

const getFileIcon = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  const IconComponent = FILE_ICONS[ext] || FILE_ICONS.default
  return <IconComponent size={14} />
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
            color: 'var(--chat-text-muted)',
            fontSize: 'var(--text-sm)',
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
            color: 'var(--chat-text-muted)',
            fontSize: 'var(--text-sm)',
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
          fontSize: 'var(--text-sm)',
          fontFamily: 'var(--font-mono)',
          color: 'var(--chat-text)',
          padding: '2px 0',
        }}
      >
        <span style={{ color: 'var(--chat-text-muted)', fontSize: '12px' }}>
          {getFileIcon(file)}
        </span>
        <span>{file}</span>
      </div>
    ))}
  </div>
)

export default GlobToolRenderer
