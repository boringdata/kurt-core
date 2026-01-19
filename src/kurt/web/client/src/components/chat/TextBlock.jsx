import { useMemo } from 'react'

/**
 * TextBlock - Renders markdown text with syntax highlighting
 *
 * Supports:
 * - Bold, italic, strikethrough
 * - Inline code with monospace font
 * - Code blocks with syntax highlighting
 * - Links
 * - Lists (ordered and unordered)
 * - Blockquotes
 */

/**
 * Inline code span
 */
const InlineCode = ({ children }) => (
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

/**
 * Parse inline markdown (bold, italic, code, links)
 */
const parseInline = (text) => {
  if (!text) return null

  const elements = []
  let remaining = text
  let key = 0

  while (remaining) {
    // Inline code
    const codeMatch = remaining.match(/^`([^`]+)`/)
    if (codeMatch) {
      elements.push(<InlineCode key={key++}>{codeMatch[1]}</InlineCode>)
      remaining = remaining.slice(codeMatch[0].length)
      continue
    }

    // Bold
    const boldMatch = remaining.match(/^\*\*([^*]+)\*\*/)
    if (boldMatch) {
      elements.push(<strong key={key++}>{boldMatch[1]}</strong>)
      remaining = remaining.slice(boldMatch[0].length)
      continue
    }

    // Italic
    const italicMatch = remaining.match(/^\*([^*]+)\*/)
    if (italicMatch) {
      elements.push(<em key={key++}>{italicMatch[1]}</em>)
      remaining = remaining.slice(italicMatch[0].length)
      continue
    }

    // Links
    const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/)
    if (linkMatch) {
      elements.push(
        <a
          key={key++}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: 'var(--chat-accent, #0078d4)',
            textDecoration: 'underline',
          }}
        >
          {linkMatch[1]}
        </a>
      )
      remaining = remaining.slice(linkMatch[0].length)
      continue
    }

    // Plain text until next special character
    const plainMatch = remaining.match(/^[^`*[]+/)
    if (plainMatch) {
      elements.push(plainMatch[0])
      remaining = remaining.slice(plainMatch[0].length)
      continue
    }

    // Single special character (not part of markdown syntax)
    elements.push(remaining[0])
    remaining = remaining.slice(1)
  }

  return elements
}

/**
 * Parse a table row into cells
 */
const parseTableRow = (row) => {
  return row
    .split('|')
    .slice(1, -1) // Remove empty first/last from | at start/end
    .map(cell => cell.trim())
}

/**
 * Split text into block-level elements
 */
const splitIntoBlocks = (text) => {
  const blocks = []
  const lines = text.split('\n')
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // Code block
    if (line.startsWith('```')) {
      const language = line.slice(3).trim()
      const codeLines = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      blocks.push({ type: 'code', content: codeLines.join('\n'), language })
      i++
      continue
    }

    // Table (lines starting with |)
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      const tableLines = []
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i])
        i++
      }
      // Parse table
      if (tableLines.length >= 2) {
        const headerRow = parseTableRow(tableLines[0])
        // Skip separator row (|---|---|)
        const dataRows = tableLines.slice(2).map(parseTableRow)
        blocks.push({ type: 'table', headers: headerRow, rows: dataRows })
      }
      continue
    }

    // Blockquote
    if (line.startsWith('> ')) {
      const quoteLines = []
      while (i < lines.length && lines[i].startsWith('> ')) {
        quoteLines.push(lines[i].slice(2))
        i++
      }
      blocks.push({ type: 'blockquote', content: quoteLines.join('\n') })
      continue
    }

    // Unordered list
    if (/^[-*]\s/.test(line)) {
      const items = []
      while (i < lines.length && /^[-*]\s/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s/, ''))
        i++
      }
      blocks.push({ type: 'list', items, ordered: false })
      continue
    }

    // Ordered list
    if (/^\d+\.\s/.test(line)) {
      const items = []
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s/, ''))
        i++
      }
      blocks.push({ type: 'list', items, ordered: true })
      continue
    }

    // Regular paragraph (skip empty lines)
    if (line.trim()) {
      const paragraphLines = []
      while (i < lines.length && lines[i].trim() && !lines[i].startsWith('```') &&
             !lines[i].startsWith('> ') && !/^[-*]\s/.test(lines[i]) &&
             !/^\d+\.\s/.test(lines[i])) {
        paragraphLines.push(lines[i])
        i++
      }
      blocks.push({ type: 'paragraph', content: paragraphLines.join(' ') })
      continue
    }

    i++
  }

  return blocks
}

/**
 * Simple markdown parser - converts markdown to React elements
 */
const parseMarkdown = (text) => {
  // Split into blocks (paragraphs, code blocks, lists)
  const blocks = splitIntoBlocks(text)

  return blocks.map((block, i) => {
    if (block.type === 'code') {
      return <CodeBlock key={i} code={block.content} language={block.language} />
    }
    if (block.type === 'blockquote') {
      return <BlockQuote key={i}>{parseInline(block.content)}</BlockQuote>
    }
    if (block.type === 'list') {
      return <List key={i} items={block.items} ordered={block.ordered} />
    }
    if (block.type === 'table') {
      return <Table key={i} headers={block.headers} rows={block.rows} />
    }
    return <Paragraph key={i}>{parseInline(block.content)}</Paragraph>
  })
}

const TextBlock = ({ text, className = '' }) => {
  const rendered = useMemo(() => {
    if (!text) return null
    return parseMarkdown(text)
  }, [text])

  return (
    <div
      className={`text-block ${className}`}
      style={{
        color: 'var(--chat-text, #cccccc)',
        fontSize: '14px',
        lineHeight: '1.6',
        wordBreak: 'break-word',
      }}
    >
      {rendered}
    </div>
  )
}

/**
 * Code block with language indicator
 */
const CodeBlock = ({ code, language }) => (
  <div
    style={{
      backgroundColor: 'var(--chat-input-bg, #3c3c3c)',
      borderRadius: 'var(--chat-radius-sm, 4px)',
      marginTop: 'var(--chat-spacing-sm, 8px)',
      marginBottom: 'var(--chat-spacing-sm, 8px)',
      overflow: 'hidden',
    }}
  >
    {language && (
      <div
        style={{
          padding: '6px 12px',
          fontSize: '11px',
          color: 'var(--chat-text-muted, #858585)',
          borderBottom: '1px solid var(--chat-border, #454545)',
          textTransform: 'lowercase',
        }}
      >
        {language}
      </div>
    )}
    <pre
      style={{
        margin: 0,
        padding: '12px',
        overflow: 'auto',
        fontFamily: 'var(--font-mono)',
        fontSize: '13px',
        lineHeight: '1.5',
        color: 'var(--chat-text, #cccccc)',
      }}
    >
      <code>{code}</code>
    </pre>
  </div>
)

/**
 * Blockquote
 */
const BlockQuote = ({ children }) => (
  <blockquote
    style={{
      margin: 'var(--chat-spacing-sm, 8px) 0',
      paddingLeft: '12px',
      borderLeft: '3px solid var(--chat-border, #454545)',
      color: 'var(--chat-text-muted, #858585)',
      fontStyle: 'italic',
    }}
  >
    {children}
  </blockquote>
)

/**
 * List (ordered or unordered)
 */
const List = ({ items, ordered }) => {
  const Tag = ordered ? 'ol' : 'ul'
  return (
    <Tag
      style={{
        margin: 'var(--chat-spacing-sm, 8px) 0',
        paddingLeft: '24px',
        listStyleType: ordered ? 'decimal' : 'disc',
      }}
    >
      {items.map((item, i) => (
        <li key={i} style={{ marginBottom: '4px' }}>
          {parseInline(item)}
        </li>
      ))}
    </Tag>
  )
}

/**
 * Paragraph
 */
const Paragraph = ({ children }) => (
  <p style={{ margin: '0 0 var(--chat-spacing-sm, 8px) 0' }}>{children}</p>
)

/**
 * Table
 */
const Table = ({ headers, rows }) => (
  <div
    style={{
      margin: 'var(--chat-spacing-sm, 8px) 0',
      borderRadius: 'var(--chat-radius-sm, 4px)',
      overflow: 'hidden',
      border: '1px solid var(--chat-border, #454545)',
    }}
  >
    <table
      style={{
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: '13px',
        fontFamily: 'var(--font-mono)',
      }}
    >
      <thead>
        <tr style={{ backgroundColor: 'var(--chat-input-bg, #3c3c3c)' }}>
          {headers.map((header, i) => (
            <th
              key={i}
              style={{
                padding: '8px 12px',
                textAlign: 'left',
                fontWeight: 600,
                color: 'var(--chat-text, #cccccc)',
                borderBottom: '1px solid var(--chat-border, #454545)',
              }}
            >
              {parseInline(header)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr
            key={i}
            style={{
              backgroundColor: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
            }}
          >
            {row.map((cell, j) => (
              <td
                key={j}
                style={{
                  padding: '8px 12px',
                  color: 'var(--chat-text, #cccccc)',
                  borderBottom: i < rows.length - 1 ? '1px solid var(--chat-border, #454545)' : 'none',
                }}
              >
                {parseInline(cell)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)

export default TextBlock
