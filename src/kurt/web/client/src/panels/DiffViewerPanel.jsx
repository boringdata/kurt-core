import React, { useState, useEffect } from 'react'
import GitDiff from '../components/GitDiff'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

// Check if file is markdown
const isMarkdownFile = (filepath) => {
  if (!filepath) return false
  const ext = filepath.split('.').pop()?.toLowerCase()
  return ['md', 'markdown', 'mdx'].includes(ext)
}

export default function DiffViewerPanel({ params: initialParams, api }) {
  const [params, setParams] = useState(initialParams || {})
  const [diff, setDiff] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('split') // 'split' | 'unified' | 'raw'

  useEffect(() => {
    if (!api) return
    const disposable = api.onDidParametersChange((event) => {
      if (event.params) {
        setParams((prev) => ({ ...prev, ...event.params }))
      }
    })
    return () => disposable.dispose()
  }, [api])

  const { path, status } = params || {}

  useEffect(() => {
    if (!path) return
    setLoading(true)
    setError(null)

    fetch(apiUrl(`/api/git/diff?path=${encodeURIComponent(path)}`))
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load diff')
        return r.json()
      })
      .then((data) => {
        setDiff(data.diff || '')
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [path])

  const isMarkdown = isMarkdownFile(path)

  // Get breadcrumb parts
  const pathParts = path ? path.split('/').filter(Boolean) : []
  const breadcrumbs = pathParts.slice(0, -1)
  const filename = pathParts[pathParts.length - 1] || ''

  const getStatusLabel = (s) => {
    switch (s) {
      case 'M': return 'Modified'
      case 'A': return 'Added'
      case 'U': return 'Untracked'
      case 'D': return 'Deleted'
      default: return 'Changed'
    }
  }

  const getStatusClass = (s) => {
    switch (s) {
      case 'M': return 'git-status-modified'
      case 'A': return 'git-status-added'
      case 'U': return 'git-status-new'
      case 'D': return 'git-status-deleted'
      default: return ''
    }
  }

  return (
    <div className="panel-content diff-viewer-panel">
      {/* Breadcrumbs */}
      {breadcrumbs.length > 0 && (
        <div className="editor-breadcrumbs">
          {breadcrumbs.map((part, index) => {
            const isLast = index === breadcrumbs.length - 1
            return (
              <span key={`${part}-${index}`} className={`crumb${isLast ? ' crumb-current' : ''}`}>
                {part}
                {!isLast && <span className="crumb-sep">›</span>}
              </span>
            )
          })}
        </div>
      )}

      {/* Toolbar */}
      <div className="diff-viewer-toolbar">
        <div className="diff-viewer-info">
          {status && (
            <span className={`git-status-badge ${getStatusClass(status)}`}>
              {getStatusLabel(status)}
            </span>
          )}
          <span className="diff-viewer-filename">{filename}</span>
        </div>
        <div className="diff-viewer-mode-selector">
          {isMarkdown ? (
            <>
              <button
                type="button"
                className={`mode-btn ${viewMode === 'split' ? 'active' : ''}`}
                onClick={() => setViewMode('split')}
              >
                Split
              </button>
              <button
                type="button"
                className={`mode-btn ${viewMode === 'unified' ? 'active' : ''}`}
                onClick={() => setViewMode('unified')}
              >
                Unified
              </button>
              <button
                type="button"
                className={`mode-btn ${viewMode === 'raw' ? 'active' : ''}`}
                onClick={() => setViewMode('raw')}
              >
                Raw
              </button>
            </>
          ) : (
            <span className="diff-viewer-raw-label">Raw Diff</span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="diff-viewer-content">
        {loading && (
          <div className="diff-loading">Loading diff...</div>
        )}
        {error && (
          <div className="diff-error">{error}</div>
        )}
        {!loading && !error && !diff && (
          <div className="diff-empty">No changes in this file.</div>
        )}
        {!loading && !error && diff && (
          isMarkdown && viewMode !== 'raw' ? (
            <div className="diff-styled">
              <GitDiff diff={diff} showFileHeader={false} viewType={viewMode} />
            </div>
          ) : (
            <div className="diff-raw">
              <pre className="diff-raw-content">{diff}</pre>
            </div>
          )
        )}
      </div>
    </div>
  )
}
