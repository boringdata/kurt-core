import { useMemo, useState } from 'react'
import { ChevronRight, ChevronDown, Brain } from 'lucide-react'
import MarkdownIt from 'markdown-it'

// Initialize markdown-it with common options
const md = new MarkdownIt({
  html: false,        // Disable HTML tags in source
  linkify: true,      // Auto-convert URLs to links
  typographer: true,  // Enable smart quotes and other typographic replacements
  breaks: true,       // Convert \n to <br>
})

/**
 * ThinkingBlock - Collapsible thinking content
 */
const ThinkingBlock = ({ content, index, expanded, onToggle }) => {
  const html = useMemo(() => md.render(content), [content])

  return (
    <div className="thinking-block">
      <button
        className="thinking-header"
        onClick={() => onToggle(index)}
        type="button"
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Brain size={14} />
        <span>Thinking</span>
      </button>
      {expanded && (
        <div
          className="thinking-content markdown-content"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )}
    </div>
  )
}

/**
 * Parse text to separate thinking blocks from regular content
 */
const parseThinkingBlocks = (text) => {
  if (!text) return []

  const parts = []
  const regex = /<thinking>([\s\S]*?)<\/thinking>/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(text)) !== null) {
    // Add text before thinking block
    if (match.index > lastIndex) {
      const before = text.slice(lastIndex, match.index).trim()
      if (before) {
        parts.push({ type: 'text', content: before })
      }
    }
    // Add thinking block
    parts.push({ type: 'thinking', content: match[1].trim() })
    lastIndex = regex.lastIndex
  }

  // Add remaining text after last thinking block
  if (lastIndex < text.length) {
    const after = text.slice(lastIndex).trim()
    if (after) {
      parts.push({ type: 'text', content: after })
    }
  }

  return parts
}

/**
 * TextBlock - Renders markdown text with collapsible thinking blocks
 */
const TextBlock = ({ text, className = '' }) => {
  const [expandedBlocks, setExpandedBlocks] = useState({})

  const parts = useMemo(() => parseThinkingBlocks(text), [text])

  const toggleBlock = (index) => {
    setExpandedBlocks(prev => ({
      ...prev,
      [index]: !prev[index]
    }))
  }

  if (!text) return null

  // If no thinking blocks, render simple markdown
  if (parts.length === 0 || (parts.length === 1 && parts[0].type === 'text')) {
    const html = md.render(text)
    return (
      <div
        className={`text-block markdown-content ${className}`}
        style={{
          color: 'var(--chat-text)',
          fontSize: '14px',
          lineHeight: '1.6',
          wordBreak: 'break-word',
        }}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    )
  }

  // Render with thinking blocks
  let thinkingIndex = 0
  return (
    <div
      className={`text-block ${className}`}
      style={{
        color: 'var(--chat-text)',
        fontSize: '14px',
        lineHeight: '1.6',
        wordBreak: 'break-word',
      }}
    >
      {parts.map((part, i) => {
        if (part.type === 'thinking') {
          const idx = thinkingIndex++
          return (
            <ThinkingBlock
              key={i}
              content={part.content}
              index={idx}
              expanded={!!expandedBlocks[idx]}
              onToggle={toggleBlock}
            />
          )
        }
        const html = md.render(part.content)
        return (
          <div
            key={i}
            className="markdown-content"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        )
      })}
    </div>
  )
}

export default TextBlock
