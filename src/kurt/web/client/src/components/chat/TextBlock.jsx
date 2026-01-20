import { useMemo } from 'react'
import MarkdownIt from 'markdown-it'

// Initialize markdown-it with common options
const md = new MarkdownIt({
  html: false,        // Disable HTML tags in source
  linkify: true,      // Auto-convert URLs to links
  typographer: true,  // Enable smart quotes and other typographic replacements
  breaks: true,       // Convert \n to <br>
})

/**
 * TextBlock - Renders markdown text using markdown-it
 */
const TextBlock = ({ text, className = '' }) => {
  const html = useMemo(() => {
    if (!text) return ''
    return md.render(text)
  }, [text])

  if (!text) return null

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

export default TextBlock
