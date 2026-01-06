import React, { useState, useEffect, useCallback } from 'react'
import Editor from '../components/Editor'
import ApprovalPanel from '../components/ApprovalPanel'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

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
    activeApproval,
    onDecision,
    onOpenFile,
  } = params || {}

  const [content, setContent] = useState(initialContent || '')
  const [contentVersion, setContentVersion] = useState(initialVersion || 1)
  const [isDirty, setIsDirty] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [externalChange, setExternalChange] = useState(false)
  const [showDiff, setShowDiff] = useState(false)
  const [diffText, setDiffText] = useState('')
  const [diffError, setDiffError] = useState('')
  const [approvalFeedback, setApprovalFeedback] = useState('')

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
      if (!isActive) return

      fetch(apiUrl(`/api/file?path=${encodeURIComponent(path)}`))
        .then((r) => r.json())
        .then((data) => {
          if (!isActive) return
          const nextContent = data.content || ''
          if (nextContent === content) return

          if (isDirty) {
            setExternalChange(true)
            return
          }

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
  }, [path, content, isDirty])

  const save = async (newContent) => {
    if (!path) return

    setIsSaving(true)
    try {
      await fetch(apiUrl(`/api/file?path=${encodeURIComponent(path)}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newContent }),
      })

      setContent(newContent)
      setIsDirty(false)
      onContentChange?.(path, newContent)
      onDirtyChange?.(path, false)

      if (showDiff) {
        loadDiff()
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

  const loadDiff = async () => {
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
    } catch (error) {
      setDiffError(error?.message || 'Failed to load git diff')
      setDiffText('')
    }
  }

  const toggleDiff = () => {
    const next = !showDiff
    setShowDiff(next)
    if (next) {
      loadDiff()
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

      {activeApproval && (
        <div className="editor-approval-banner">
          <span className="approval-badge">{activeApproval.tool_name}</span>
          <span className="approval-info">
            {activeApproval.session_provider && (
              <span className="approval-provider">{activeApproval.session_provider}</span>
            )}
            {activeApproval.session_name && (
              <span className="approval-session-name">{activeApproval.session_name}</span>
            )}
            {activeApproval.session_id && (
              <span className="approval-session-id">{activeApproval.session_id.slice(0, 8)}</span>
            )}
            {!activeApproval.session_provider && !activeApproval.session_name && !activeApproval.session_id && (
              'Approval Required'
            )}
          </span>
          <div className="approval-banner-actions">
            <button
              type="button"
              className="approval-deny"
              onClick={() => {
                console.log('Deny clicked', { id: activeApproval.id, onDecision, approvalFeedback })
                onDecision?.(activeApproval.id, 'deny', approvalFeedback)
              }}
            >
              Deny
            </button>
            <button
              type="button"
              className="approval-allow"
              onClick={() => {
                console.log('Allow clicked', { id: activeApproval.id, onDecision, approvalFeedback })
                onDecision?.(activeApproval.id, 'allow', approvalFeedback)
              }}
            >
              Allow
            </button>
          </div>
        </div>
      )}

      {activeApproval ? (
        <ApprovalPanel
          request={activeApproval}
          onFeedbackChange={setApprovalFeedback}
        />
      ) : (
        <Editor
          content={content}
          contentVersion={contentVersion}
          isDirty={isDirty}
          isSaving={isSaving}
          onChange={handleChange}
          onAutoSave={handleAutoSave}
          showDiffToggle={Boolean(path)}
          diffEnabled={showDiff}
          diffText={diffText}
          diffError={diffError}
          onToggleDiff={toggleDiff}
        />
      )}
    </div>
  )
}
