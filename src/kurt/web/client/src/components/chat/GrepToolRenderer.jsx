import ToolUseBlock, { ToolOutput, ToolError, InlineCode } from './ToolUseBlock'

/**
 * GrepToolRenderer - Displays code search operations
 *
 * From reference screenshots:
 * - Header: "Grep" + search pattern
 * - Results: File paths with matching lines
 * - Line numbers and highlighted matches
 */

const escapeRegex = (str) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const GrepToolRenderer = ({
  pattern,
  path,
  results = [],
  matchCount,
  error,
  status = 'complete',
}) => {
  // Build description
  let description = (
    <>
      <InlineCode>{pattern}</InlineCode>
      {path && (
        <span style={{ marginLeft: '6px', color: 'var(--chat-text-muted, #858585)' }}>
          in {path}
        </span>
      )}
    </>
  )

  const hasResults = results.length > 0
  const totalMatches = matchCount || results.reduce((sum, r) => sum + (r.matches?.length || 1), 0)

  return (
    <ToolUseBlock
      toolName="Grep"
      description={description}
      status={status}
      collapsible={results.length > 5}
      defaultExpanded={results.length <= 10}
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
          Searching...
        </div>
      ) : hasResults ? (
        <SearchResults results={results} pattern={pattern} />
      ) : (
        <div
          style={{
            color: 'var(--chat-text-muted, #858585)',
            fontSize: '13px',
          }}
        >
          No matches found
        </div>
      )}

      {hasResults && totalMatches > 0 && (
        <div
          style={{
            marginTop: 'var(--chat-spacing-xs, 4px)',
            fontSize: '12px',
            color: 'var(--chat-text-muted, #858585)',
          }}
        >
          {totalMatches} match{totalMatches !== 1 ? 'es' : ''} in {results.length} file{results.length !== 1 ? 's' : ''}
        </div>
      )}
    </ToolUseBlock>
  )
}

/**
 * SearchResults - Renders grouped search results by file
 */
const SearchResults = ({ results, pattern }) => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--chat-spacing-sm, 8px)',
    }}
  >
    {results.map((result, i) => (
      <FileResult key={i} result={result} pattern={pattern} />
    ))}
  </div>
)

/**
 * FileResult - Single file with its matching lines
 */
const FileResult = ({ result, pattern }) => {
  const { file, matches = [] } = result

  // If matches is just a string (single match), convert to array
  const matchList = Array.isArray(matches) ? matches : [{ line: 1, content: matches }]

  return (
    <div>
      {/* File path */}
      <div
        style={{
          fontSize: '12px',
          color: 'var(--chat-accent, #0078d4)',
          fontFamily: 'var(--font-mono)',
          marginBottom: '4px',
        }}
      >
        {file}
      </div>

      {/* Matching lines */}
      <div
        style={{
          backgroundColor: 'var(--chat-input-bg, #3c3c3c)',
          borderRadius: 'var(--chat-radius-sm, 4px)',
          overflow: 'hidden',
        }}
      >
        {matchList.map((match, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              fontSize: '13px',
              fontFamily: 'var(--font-mono)',
              lineHeight: '1.5',
            }}
          >
            {/* Line number */}
            <span
              style={{
                minWidth: '40px',
                padding: '0 8px',
                color: 'var(--chat-text-muted, #858585)',
                backgroundColor: 'rgba(0, 0, 0, 0.2)',
                textAlign: 'right',
                flexShrink: 0,
              }}
            >
              {match.line || i + 1}
            </span>
            {/* Line content */}
            <span
              style={{
                padding: '0 8px',
                color: 'var(--chat-text, #cccccc)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                flex: 1,
              }}
            >
              <HighlightedContent content={match.content || match} pattern={pattern} />
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * HighlightedContent - Highlights pattern matches in content
 */
const HighlightedContent = ({ content, pattern }) => {
  if (!pattern || !content) return content

  try {
    const regex = new RegExp(`(${escapeRegex(pattern)})`, 'gi')
    const parts = content.split(regex)

    return parts.map((part, i) => {
      const isMatch = part.toLowerCase() === pattern.toLowerCase()
      return isMatch ? (
        <mark
          key={i}
          style={{
            backgroundColor: 'rgba(230, 180, 80, 0.4)',
            color: '#e6b450',
            borderRadius: '2px',
          }}
        >
          {part}
        </mark>
      ) : (
        part
      )
    })
  } catch {
    return content
  }
}

export default GrepToolRenderer
