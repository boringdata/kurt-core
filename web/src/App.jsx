import React, { useState, useEffect, useCallback, useRef } from 'react'
import FileTree from './components/FileTree'
import Editor from './components/Editor'
import GitDiff from './components/GitDiff'
import ApprovalPanel from './components/ApprovalPanel'
import Terminal from './components/Terminal'
import TabBar from './components/TabBar'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

export default function App() {
  const [tabs, setTabs] = useState([])
  const [activeTab, setActiveTab] = useState(null)
  const [showDiff, setShowDiff] = useState(false)
  const [diffText, setDiffText] = useState('')
  const [diffError, setDiffError] = useState('')
  const [diffLoading, setDiffLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [approvalQueue, setApprovalQueue] = useState([])
  const lastApprovalId = useRef(null)
  const [gitStatus, setGitStatus] = useState({})

  const fetchGitStatus = useCallback(() => {
    fetch(apiUrl('/api/git/status'))
      .then((r) => r.json())
      .then((data) => {
        if (data.available && data.files) {
          setGitStatus(data.files)
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetchGitStatus()
    const interval = setInterval(fetchGitStatus, 5000)
    return () => clearInterval(interval)
  }, [fetchGitStatus])

  const currentTab = tabs.find((t) => t.path === activeTab)
  const content = currentTab?.content || ''
  const contentVersion = currentTab?.contentVersion || 0
  const isDirty = currentTab?.isDirty || false
  const externalChange = currentTab?.externalChange || false
  const activeApproval = approvalQueue[0] || null

  const updateTab = useCallback((path, updates) => {
    setTabs((prev) =>
      prev.map((t) => (t.path === path ? { ...t, ...updates } : t))
    )
  }, [])

  const openFile = useCallback((path) => {
    const existing = tabs.find((t) => t.path === path)
    if (existing) {
      setActiveTab(path)
      return
    }

    fetch(apiUrl(`/api/file?path=${encodeURIComponent(path)}`))
      .then((r) => r.json())
      .then((data) => {
        const newTab = {
          path,
          content: data.content || '',
          contentVersion: 1,
          isDirty: false,
          externalChange: false,
        }
        setTabs((prev) => [...prev, newTab])
        setActiveTab(path)
        setDiffText('')
        setDiffError('')
      })
      .catch(() => {
        const newTab = {
          path,
          content: '',
          contentVersion: 1,
          isDirty: false,
          externalChange: false,
        }
        setTabs((prev) => [...prev, newTab])
        setActiveTab(path)
        setDiffText('')
        setDiffError('')
      })
  }, [tabs])

  const closeTab = useCallback((path) => {
    setTabs((prev) => {
      const idx = prev.findIndex((t) => t.path === path)
      const newTabs = prev.filter((t) => t.path !== path)

      if (path === activeTab && newTabs.length > 0) {
        const newIdx = Math.min(idx, newTabs.length - 1)
        setActiveTab(newTabs[newIdx].path)
      } else if (newTabs.length === 0) {
        setActiveTab(null)
      }

      return newTabs
    })
  }, [activeTab])

  useEffect(() => {
    if (!activeTab) return
    let isActive = true
    const interval = setInterval(() => {
      if (!isActive) return
      const tab = tabs.find((t) => t.path === activeTab)
      if (!tab) return

      fetch(apiUrl(`/api/file?path=${encodeURIComponent(activeTab)}`))
        .then((r) => r.json())
        .then((data) => {
          if (!isActive) return
          const nextContent = data.content || ''
          if (nextContent === tab.content) return

          if (tab.isDirty) {
            updateTab(activeTab, { externalChange: true })
            return
          }

          updateTab(activeTab, {
            content: nextContent,
            isDirty: false,
            externalChange: false,
            contentVersion: tab.contentVersion + 1,
          })
        })
        .catch(() => {})
    }, 2000)

    return () => {
      isActive = false
      clearInterval(interval)
    }
  }, [activeTab, tabs, updateTab])

  useEffect(() => {
    let isActive = true

    const fetchApprovals = () => {
      fetch(apiUrl('/api/approval/pending'))
        .then((r) => r.json())
        .then((data) => {
          if (!isActive) return
          setApprovalQueue(data.requests || [])
        })
        .catch(() => {})
    }

    fetchApprovals()
    const interval = setInterval(fetchApprovals, 1000)

    return () => {
      isActive = false
      clearInterval(interval)
    }
  }, [])

  const save = async (newContent) => {
    if (!activeTab) return
    const tab = tabs.find((t) => t.path === activeTab)
    if (!tab || newContent === tab.content) return

    setIsSaving(true)
    try {
      await fetch(apiUrl(`/api/file?path=${encodeURIComponent(activeTab)}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newContent }),
      })

      updateTab(activeTab, { content: newContent, isDirty: false })

      if (showDiff) {
        loadDiff()
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleChange = (newContent) => {
    if (!activeTab) return
    const tab = tabs.find((t) => t.path === activeTab)
    if (!tab) return
    updateTab(activeTab, { isDirty: newContent !== tab.content })
  }

  const handleAutoSave = (newContent) => {
    if (!activeTab) return
    const tab = tabs.find((t) => t.path === activeTab)
    if (!tab || newContent === tab.content) return
    save(newContent)
  }

  const loadDiff = async () => {
    if (!activeTab) return
    setDiffLoading(true)
    setDiffError('')
    try {
      const response = await fetch(
        apiUrl(`/api/git/diff?path=${encodeURIComponent(activeTab)}`),
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
    } finally {
      setDiffLoading(false)
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
    if (!activeTab) return
    fetch(apiUrl(`/api/file?path=${encodeURIComponent(activeTab)}`))
      .then((r) => r.json())
      .then((data) => {
        const tab = tabs.find((t) => t.path === activeTab)
        if (!tab) return
        updateTab(activeTab, {
          content: data.content || '',
          isDirty: false,
          externalChange: false,
          contentVersion: tab.contentVersion + 1,
        })
      })
      .catch(() => {})
  }

  const handleDecision = async (requestId, decision, reason) => {
    await fetch(apiUrl('/api/approval/decision'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: requestId, decision, reason }),
    })
    setApprovalQueue((prev) => prev.filter((req) => req.id !== requestId))
  }

  const handleOpenFile = (path) => {
    if (!path) return
    openFile(path)
  }

  useEffect(() => {
    if (!activeApproval || !activeApproval.id) return
    if (lastApprovalId.current === activeApproval.id) return
    lastApprovalId.current = activeApproval.id
    const targetPath = activeApproval.project_path || activeApproval.file_path
    if (targetPath) {
      openFile(targetPath)
    }
  }, [activeApproval, openFile])

  return (
    <div className="app">
      <div className="sidebar">
        <FileTree onOpen={openFile} />
      </div>
      <div className="editor">
        <TabBar
          tabs={tabs}
          activeTab={activeTab}
          gitStatus={gitStatus}
          onSelect={setActiveTab}
          onClose={closeTab}
        />
        <div className="editor-header">
          <div className="editor-title">
            {activeTab || 'No file selected'}
            {isDirty ? ' •' : ''}
          </div>
          <button
            type="button"
            className="diff-toggle"
            onClick={toggleDiff}
            disabled={!activeTab || Boolean(activeApproval)}
          >
            {showDiff ? 'Hide git diff' : 'Show git diff'}
          </button>
        </div>
        {externalChange ? (
          <div className="notice">
            File changed on disk.
            <button type="button" onClick={reloadFromDisk}>
              Reload
            </button>
          </div>
        ) : null}
        {activeApproval ? (
          <ApprovalPanel
            request={activeApproval}
            onDecision={handleDecision}
            onOpenFile={handleOpenFile}
          />
        ) : showDiff ? (
          <div className="diff-panel">
            <div className="diff-header">
              <span>Git diff</span>
              <button type="button" onClick={loadDiff} disabled={diffLoading}>
                {diffLoading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
            {diffError ? <div className="diff-error">{diffError}</div> : null}
            <GitDiff diff={diffText} />
          </div>
        ) : activeTab ? (
          <Editor
            content={content}
            contentVersion={contentVersion}
            isDirty={isDirty}
            isSaving={isSaving}
            onChange={handleChange}
            onAutoSave={handleAutoSave}
          />
        ) : (
          <div className="editor-empty">
            <p>Open a file from the sidebar to start editing</p>
          </div>
        )}
      </div>
      <div className="terminal-panel">
        <div className="terminal-header">
          <div className="terminal-title">
            <span className="status-dot" />
            Claude Code
          </div>
          <div className="terminal-meta">Session</div>
        </div>
        <div className="terminal-body">
          <Terminal />
        </div>
      </div>
    </div>
  )
}
