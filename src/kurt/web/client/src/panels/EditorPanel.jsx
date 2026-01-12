import React, { useState, useEffect, useMemo, useCallback } from 'react'
import Editor from '../components/Editor'
import CodeEditor from '../components/CodeEditor'
import GitDiff from '../components/GitDiff'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

// Check if file is markdown
const isMarkdownFile = (filepath) => {
  if (!filepath) return false
  const ext = filepath.split('.').pop()?.toLowerCase()
  return ['md', 'markdown', 'mdx'].includes(ext)
}

export default function EditorPanel({ params: initialParams, api }) {
  // Track params updates from dockview
  const [params, setParams] = useState(initialParams || {})

  useEffect(() => {
    if (!api) return
    const disposable = api.onDidParametersChange((event) => {
      if (event.params) {
        setParams((prev) => ({ ...prev, ...event.params }))
      }
    })
    return () => disposable.dispose()
  }, [api])

  const {
    path,
    initialContent,
    contentVersion: initialVersion,
    onContentChange,
    onDirtyChange,
    initialMode,
  } = params || {}

  const [content, setContent] = useState(initialContent || '')
  const [contentVersion, setContentVersion] = useState(initialVersion || 1)
  const [isDirty, setIsDirty] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [externalChange, setExternalChange] = useState(false)
  const [editorMode, setEditorMode] = useState(initialMode || 'rendered') // 'rendered' | 'diff' | 'git-diff'
  const [diffText, setDiffText] = useState('')
  const [diffError, setDiffError] = useState('')
  const [originalContent, setOriginalContent] = useState(null)
  const [initialModeApplied, setInitialModeApplied] = useState(false)

  const loadDiff = useCallback(async () => {
    if (!path) return
    setDiffError('')
    try {
      const response = await fetch(
        apiUrl(`/api/git/diff?path=${encodeURIComponent(path)}`)
      )
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to load git diff')
      }
      const data = await response.json()
      setDiffText(data.diff || '')
    } catch (err) {
      setDiffError(err?.message || 'Failed to load git diff')
      setDiffText('')
    }
  }, [path])

  const loadOriginalContent = useCallback(async () => {
    if (!path) return
    try {
      const response = await fetch(
        apiUrl(`/api/git/show?path=${encodeURIComponent(path)}`)
      )
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to load original content')
      }
      const data = await response.json()
      setOriginalContent(data.is_new ? '' : (data.content || ''))
    } catch (err) {
      setOriginalContent(null)
      setDiffError(err?.message || 'Failed to load original content')
    }
  }, [path])

  // Apply initial mode when params change (e.g., opening from git changes)
  useEffect(() => {
    if (initialMode && !initialModeApplied) {
      setEditorMode(initialMode)
      setInitialModeApplied(true)
      if (initialMode === 'git-diff') {
        loadDiff()
      } else if (initialMode === 'diff') {
        loadOriginalContent()
      }
    }
  }, [initialMode, initialModeApplied, loadDiff, loadOriginalContent])

  // Sync content from parent when it changes
  useEffect(() => {
    if (initialContent !== undefined && initialContent !== content && !isDirty) {
      setContent(initialContent)
      setContentVersion((v) => v + 1)
    }
  }, [initialContent])

  // Poll for external changes
  useEffect(() => {
    if (!path) return
    let isActive = true

    const interval = setInterval(() => {
      // Don't poll while saving or if dirty - prevents race conditions
      if (!isActive || isSaving || isDirty) return

      fetch(apiUrl(`/api/file?path=${encodeURIComponent(path)}`))
        .then((r) => r.json())
        .then((data) => {
          if (!isActive || isSaving || isDirty) return
          const nextContent = data.content || ''
          if (nextContent === content) return

          setContent(nextContent)
          setContentVersion((v) => v + 1)
          setExternalChange(false)
        })
        .catch(() => {})
    }, 2000)

    return () => {
      isActive = false
      clearInterval(interval)
    }
  }, [path, content, isDirty, isSaving])

  const save = async (newContent) => {
    if (!path) return

    // Update content state BEFORE the API call to prevent race condition with polling
    // This ensures the poll comparison uses the new content
    setContent(newContent)
    setIsSaving(true)
    try {
      await fetch(apiUrl(`/api/file?path=${encodeURIComponent(path)}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newContent }),
      })

      setIsDirty(false)
      onContentChange?.(path, newContent)
      onDirtyChange?.(path, false)

      // Reload diff data if in diff mode
      if (editorMode === 'git-diff') {
        loadDiff()
      } else if (editorMode === 'diff') {
        loadOriginalContent()
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleChange = (newContent) => {
    const dirty = newContent !== content
    setIsDirty(dirty)
    onDirtyChange?.(path, dirty)
  }

  const handleAutoSave = (newContent) => {
    if (newContent === content) return
    save(newContent)
  }

  const handleModeChange = (newMode) => {
    setEditorMode(newMode)
    setDiffError('')
    if (newMode === 'git-diff') {
      loadDiff()
    } else if (newMode === 'diff') {
      loadOriginalContent()
    }
  }

  const reloadFromDisk = () => {
    if (!path) return
    fetch(apiUrl(`/api/file?path=${encodeURIComponent(path)}`))
      .then((r) => r.json())
      .then((data) => {
        setContent(data.content || '')
        setIsDirty(false)
        setExternalChange(false)
        setContentVersion((v) => v + 1)
      })
      .catch(() => {})
  }

  // Only show folder path in breadcrumbs (filename is already in tab)
  const pathParts = path ? path.split('/').filter(Boolean) : []
  const breadcrumbs = pathParts.slice(0, -1) // Exclude filename
  const filename = pathParts[pathParts.length - 1] || ''

  // Determine if this is a markdown file
  const isMarkdown = useMemo(() => isMarkdownFile(path), [path])

  return (
    <div className="panel-content editor-panel-content">
      {externalChange && (
        <div className="notice">
          File changed on disk.
          <button type="button" onClick={reloadFromDisk}>
            Reload
          </button>
        </div>
      )}

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

      {isMarkdown ? (
        <Editor
          content={content}
          contentVersion={contentVersion}
          isDirty={isDirty}
          isSaving={isSaving}
          onChange={handleChange}
          onAutoSave={handleAutoSave}
          showDiffToggle={Boolean(path)}
          editorMode={editorMode}
          diffText={diffText}
          diffError={diffError}
          originalContent={originalContent}
          onModeChange={handleModeChange}
        />
      ) : (
        <div className="code-viewer-container">
          {/* Mode selector for non-markdown files */}
          <div className="code-viewer-toolbar">
            <div className="editor-mode-selector">
              <button
                type="button"
                className={`mode-btn ${editorMode === 'rendered' ? 'active' : ''}`}
                onClick={() => handleModeChange('rendered')}
              >
                Code
              </button>
              <button
                type="button"
                className={`mode-btn ${editorMode === 'git-diff' ? 'active' : ''}`}
                onClick={() => handleModeChange('git-diff')}
              >
                Diff
              </button>
            </div>
          </div>
          {editorMode === 'git-diff' ? (
            <div className="code-diff-view">
              {diffError && <div className="diff-error">{diffError}</div>}
              <GitDiff diff={diffText} showFileHeader={false} />
            </div>
          ) : (
            <CodeEditor
              content={content}
              contentVersion={contentVersion}
              filename={filename}
              isDirty={isDirty}
              isSaving={isSaving}
              onChange={handleChange}
              onAutoSave={handleAutoSave}
              className="editor-code-editor"
            />
          )}
        </div>
      )}
    </div>
  )
}
