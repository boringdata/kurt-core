import { useState, useEffect, useCallback, useRef } from 'react'
import { DockviewReact } from 'dockview-react'
import 'dockview-react/dist/styles/dockview.css'

import FileTreePanel from './panels/FileTreePanel'
import EditorPanel from './panels/EditorPanel'
import TerminalPanel from './panels/TerminalPanel'
import EmptyPanel from './panels/EmptyPanel'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

const components = {
  filetree: FileTreePanel,
  editor: EditorPanel,
  terminal: TerminalPanel,
  empty: EmptyPanel,
}

const KNOWN_COMPONENTS = new Set(Object.keys(components))

const getFileName = (path) => {
  const parts = path.split('/')
  return parts[parts.length - 1]
}

const STORAGE_KEY = 'kurt-web-open-tabs'
const LAYOUT_STORAGE_KEY = 'kurt-web-layout'

// Load saved tabs from localStorage
const loadSavedTabs = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    // Ignore parse errors
  }
  return []
}

// Save open tabs to localStorage
const saveTabs = (paths) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(paths))
  } catch (e) {
    // Ignore storage errors
  }
}

const loadLayout = () => {
  try {
    const raw = localStorage.getItem(LAYOUT_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed?.panels && typeof parsed.panels === 'object') {
      const panels = Object.values(parsed.panels)
      const hasUnknown = panels.some(
        (panel) =>
          panel?.contentComponent &&
          !KNOWN_COMPONENTS.has(panel.contentComponent),
      )
      if (hasUnknown) {
        localStorage.removeItem(LAYOUT_STORAGE_KEY)
        return null
      }
    }
    return parsed
  } catch (e) {
    return null
  }
}

const pruneEmptyGroups = (api) => {
  if (!api || !Array.isArray(api.groups)) return false
  const groups = [...api.groups]
  let removed = false

  groups.forEach((group) => {
    const panels = Array.isArray(group?.panels) ? group.panels : []
    if (panels.length === 0) {
      api.removeGroup(group)
      removed = true
      return
    }
    const hasKnownPanel = panels.some((panel) =>
      KNOWN_COMPONENTS.has(panel?.api?.component),
    )
    if (!hasKnownPanel) {
      api.removeGroup(group)
      removed = true
    }
  })

  return removed
}

const saveLayout = (layout) => {
  try {
    localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(layout))
  } catch (e) {
    // Ignore storage errors
  }
}

export default function App() {
  const [dockApi, setDockApi] = useState(null)
  const [tabs, setTabs] = useState({}) // path -> { content, isDirty }
  const [approvalQueue, setApprovalQueue] = useState([])
  const [gitStatus, setGitStatus] = useState({})
  const [activeFile, setActiveFile] = useState(null)
  const lastApprovalId = useRef(null)
  const dismissedApprovalsRef = useRef(new Set())
  const centerGroupRef = useRef(null)
  const isInitialized = useRef(false)
  const openFileRef = useRef(null)
  const layoutRestored = useRef(false)
  const [projectRoot, setProjectRoot] = useState('')

  const activeApproval = approvalQueue[0] || null

  // Fetch git status
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

  // Fetch approvals
  useEffect(() => {
    let isActive = true

    const fetchApprovals = () => {
      fetch(apiUrl('/api/approval/pending'))
        .then((r) => r.json())
        .then((data) => {
          if (!isActive) return
          const requests = Array.isArray(data.requests) ? data.requests : []
          const filtered = requests.filter(
            (req) => !dismissedApprovalsRef.current.has(req.id),
          )
          setApprovalQueue(filtered)
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

  const handleDecision = async (requestId, decision, reason) => {
    if (requestId) {
      dismissedApprovalsRef.current.add(requestId)
      setApprovalQueue((prev) => prev.filter((req) => req.id !== requestId))
    } else {
      setApprovalQueue([])
    }
    try {
      await fetch(apiUrl('/api/approval/decision'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: requestId, decision, reason }),
      })
    } catch {
      // Ignore decision errors; UI already dismissed.
    }
  }

  const normalizeApprovalPath = useCallback(
    (approval) => {
      if (!approval) return ''
      if (approval.project_path) return approval.project_path
      const filePath = approval.file_path || ''
      if (!filePath) return ''
      if (projectRoot) {
        const root = projectRoot.endsWith('/') ? projectRoot : `${projectRoot}/`
        if (filePath.startsWith(root)) {
          return filePath.slice(root.length)
        }
      }
      return filePath
    },
    [projectRoot],
  )

  const shouldShowApprovalForPath = useCallback(
    (path) => {
      if (!activeApproval) return false
      const approvalPath = normalizeApprovalPath(activeApproval)
      return (
        (approvalPath && approvalPath === path) ||
        activeApproval.project_path === path ||
        activeApproval.file_path === path
      )
    },
    [activeApproval, normalizeApprovalPath],
  )

  // Open file in a specific position (used for drag-drop)
  const openFileAtPosition = useCallback(
    (path, position) => {
      if (!dockApi) return

      const panelId = `editor-${path}`
      const existingPanel = dockApi.getPanel(panelId)

      if (existingPanel) {
        existingPanel.api.setActive()
        return
      }

      const emptyPanel = dockApi.getPanel('empty-center')
      const centerGroup = centerGroupRef.current
      if (centerGroup) {
        centerGroup.header.hidden = false
      }

      const addEditorPanel = (content) => {
        setTabs((prev) => ({
          ...prev,
          [path]: { content, isDirty: false },
        }))

        const panel = dockApi.addPanel({
          id: panelId,
          component: 'editor',
          title: getFileName(path),
          position,
          params: {
            path,
            initialContent: content,
            contentVersion: 1,
            onContentChange: (p, newContent) => {
              setTabs((prev) => ({
                ...prev,
                [p]: { ...prev[p], content: newContent },
              }))
            },
            onDirtyChange: (p, dirty) => {
              setTabs((prev) => ({
                ...prev,
                [p]: { ...prev[p], isDirty: dirty },
              }))
              const panel = dockApi.getPanel(`editor-${p}`)
              if (panel) {
                panel.api.setTitle(getFileName(p) + (dirty ? ' *' : ''))
              }
            },
            activeApproval: shouldShowApprovalForPath(path) ? activeApproval : null,
            onDecision: handleDecision,
            onOpenFile: (p) => openFileRef.current?.(p),
          },
        })

        if (emptyPanel) {
          emptyPanel.api.close()
        }
        if (panel?.group) {
          panel.group.header.hidden = false
          centerGroupRef.current = panel.group
        }
      }

      fetch(apiUrl(`/api/file?path=${encodeURIComponent(path)}`))
        .then((r) => r.json())
        .then((data) => {
          addEditorPanel(data.content || '')
        })
        .catch(() => {
          addEditorPanel('')
        })
    },
    [dockApi, handleDecision, activeApproval, shouldShowApprovalForPath]
  )

  const openFile = useCallback(
    (path) => {
      if (!dockApi) return false

      const panelId = `editor-${path}`
      const existingPanel = dockApi.getPanel(panelId)

      if (existingPanel) {
        existingPanel.api.setActive()
        return true
      }

      // Default position is center group
      const centerGroup = centerGroupRef.current
      const position = centerGroup
        ? { referenceGroup: centerGroup }
        : { direction: 'right', referencePanel: 'filetree' }

      openFileAtPosition(path, position)
      return true
    },
    [dockApi, openFileAtPosition]
  )

  const openFileToSide = useCallback(
    (path) => {
      if (!dockApi) return

      const panelId = `editor-${path}`
      const existingPanel = dockApi.getPanel(panelId)

      if (existingPanel) {
        existingPanel.api.setActive()
        return
      }

      // Find the active editor panel to split from (not terminal/filetree)
      const activePanel = dockApi.activePanel
      let position

      if (activePanel && activePanel.id.startsWith('editor-')) {
        // Split to the right of the current editor
        position = { direction: 'right', referencePanel: activePanel.id }
      } else if (centerGroupRef.current) {
        // Use center group if no editor is active
        position = { direction: 'right', referenceGroup: centerGroupRef.current }
      } else {
        // Fallback: to the right of filetree (but will be left of terminal)
        position = { direction: 'right', referencePanel: 'filetree' }
      }

      openFileAtPosition(path, position)
    },
    [dockApi, openFileAtPosition]
  )

  // Keep ref updated for use in callbacks
  openFileRef.current = openFile

  // Auto-open file when approval comes in
  useEffect(() => {
    if (!activeApproval || !activeApproval.id) return
    if (lastApprovalId.current === activeApproval.id) return
    const targetPath = normalizeApprovalPath(activeApproval)
    if (!targetPath) return
    const didOpen = openFile(targetPath)
    if (didOpen) {
      lastApprovalId.current = activeApproval.id
    }
  }, [activeApproval, openFile, normalizeApprovalPath])

  useEffect(() => {
    if (!dockApi) return
    // Update all editor panels, not just those tracked in tabs state
    // This handles panels restored from saved layout
    const allPanels = dockApi.panels || []
    allPanels.forEach((panel) => {
      if (!panel.id.startsWith('editor-')) return
      const path = panel.id.replace('editor-', '')
      panel.api.updateParameters({
        activeApproval: shouldShowApprovalForPath(path) ? activeApproval : null,
        onDecision: handleDecision,
        onOpenFile: openFile,
      })
    })
  }, [dockApi, tabs, activeApproval, handleDecision, openFile, shouldShowApprovalForPath])

  const onReady = (event) => {
    const api = event.api
    setDockApi(api)

    const applyLockedPanels = () => {
      const filetreePanel = api.getPanel('filetree')
      const terminalPanel = api.getPanel('terminal')

      const filetreeGroup = filetreePanel?.group
      if (filetreeGroup) {
        filetreeGroup.locked = true
        filetreeGroup.header.hidden = true
        filetreeGroup.api.setConstraints({
          minimumWidth: 280,
          maximumWidth: 280,
        })
      }

      const terminalGroup = terminalPanel?.group
      if (terminalGroup) {
        terminalGroup.locked = true
        terminalGroup.header.hidden = true
        terminalGroup.api.setConstraints({
          minimumWidth: 400,
          maximumWidth: 400,
        })
      }
    }

    const ensureCorePanels = () => {
      let filetreePanel = api.getPanel('filetree')
      if (!filetreePanel) {
        filetreePanel = api.addPanel({
          id: 'filetree',
          component: 'filetree',
          title: 'Files',
          params: { onOpenFile: () => {} },
        })
      }

      let terminalPanel = api.getPanel('terminal')
      if (!terminalPanel) {
        terminalPanel = api.addPanel({
          id: 'terminal',
          component: 'terminal',
          title: 'Code Sessions',
          position: { direction: 'right', referencePanel: 'filetree' },
        })
      }

      const panels = Array.isArray(api.panels)
        ? api.panels
        : typeof api.getPanels === 'function'
          ? api.getPanels()
          : []
      const editorPanels = panels.filter((panel) =>
        panel.id.startsWith('editor-'),
      )
      if (editorPanels.length > 0) {
        centerGroupRef.current = editorPanels[0].group
      } else {
        const emptyPanel =
          api.getPanel('empty-center') ||
          api.addPanel({
            id: 'empty-center',
            component: 'empty',
            title: '',
            position: { direction: 'right', referencePanel: 'filetree' },
          })
        centerGroupRef.current = emptyPanel?.group
        if (emptyPanel?.group) {
          emptyPanel.group.header.hidden = true
        }
      }

      applyLockedPanels()
    }

    const savedLayout = loadLayout()
    if (savedLayout && typeof api.fromJSON === 'function') {
      try {
        api.fromJSON(savedLayout)
        layoutRestored.current = true
      } catch (error) {
        layoutRestored.current = false
      }
    }

    ensureCorePanels()

    if (!layoutRestored.current) {
      // Set initial sizes
      const filetreeGroup = api.getPanel('filetree')?.group
      const terminalGroup = api.getPanel('terminal')?.group
      if (filetreeGroup) {
        api.getGroup(filetreeGroup.id)?.api.setSize({ width: 280 })
      }
      if (terminalGroup) {
        api.getGroup(terminalGroup.id)?.api.setSize({ width: 400 })
      }
    } else {
      const pruned = pruneEmptyGroups(api)
      if (pruned && typeof api.toJSON === 'function') {
        saveLayout(api.toJSON())
      }
    }

    // Handle panel close to clean up tabs state
    api.onDidRemovePanel((e) => {
      if (e.id.startsWith('editor-')) {
        const path = e.id.replace('editor-', '')
        setTabs((prev) => {
          const next = { ...prev }
          delete next[path]
          return next
        })
      }
    })


    // When all editors are closed, show the empty panel again
    api.onDidRemovePanel(() => {
      // Check if center group has any editor panels left
      const centerGroup = centerGroupRef.current
      if (!centerGroup) return

      const hasEditors = centerGroup.panels.some(p => p.id.startsWith('editor-'))
      const hasEmpty = centerGroup.panels.some(p => p.id === 'empty-center')

      if (!hasEditors && !hasEmpty) {
        // Re-add empty panel
        api.addPanel({
          id: 'empty-center',
          component: 'empty',
          title: '',
          position: { referenceGroup: centerGroup },
        })
        centerGroup.header.hidden = true
      }
    })

    const saveLayoutNow = () => {
      if (typeof api.toJSON !== 'function') return
      saveLayout(api.toJSON())
    }

    if (typeof api.onDidLayoutChange === 'function') {
      api.onDidLayoutChange(() => {
        saveLayoutNow()
      })
    }

    window.addEventListener('beforeunload', saveLayoutNow)

    // Mark as initialized immediately - tabs will be restored via useEffect
    isInitialized.current = true
  }

  // Fetch project root for copy path feature
  useEffect(() => {
    fetch(apiUrl('/api/project'))
      .then((r) => r.json())
      .then((data) => setProjectRoot(data.root || ''))
      .catch(() => {})
  }, [])

  // Track active panel to highlight in file tree
  useEffect(() => {
    if (!dockApi) return
    const disposable = dockApi.onDidActivePanelChange((panel) => {
      if (panel && panel.id && panel.id.startsWith('editor-')) {
        const path = panel.id.replace('editor-', '')
        setActiveFile(path)
      } else {
        setActiveFile(null)
      }
    })
    return () => disposable.dispose()
  }, [dockApi])

  // Update filetree panel params when openFile changes
  useEffect(() => {
    if (!dockApi) return
    const filetreePanel = dockApi.getPanel('filetree')
    if (filetreePanel) {
      filetreePanel.api.updateParameters({
        onOpenFile: openFile,
        onOpenFileToSide: openFileToSide,
        projectRoot,
        activeFile,
      })
    }
  }, [dockApi, openFile, openFileToSide, projectRoot, activeFile])

  // Restore saved tabs when dockApi becomes available
  const hasRestoredTabs = useRef(false)
  useEffect(() => {
    if (!dockApi || hasRestoredTabs.current) return
    hasRestoredTabs.current = true

    if (layoutRestored.current) {
      return
    }

    const savedPaths = loadSavedTabs()
    if (savedPaths.length > 0) {
      // Small delay to ensure layout is ready
      setTimeout(() => {
        savedPaths.forEach((path) => {
          openFile(path)
        })
      }, 50)
    }
  }, [dockApi, openFile])

  // Save open tabs to localStorage whenever tabs change (but not on initial empty state)
  useEffect(() => {
    if (!isInitialized.current) return
    const paths = Object.keys(tabs)
    saveTabs(paths)
  }, [tabs])

  // Handle external drag events (files from FileTree)
  const showDndOverlay = (event) => {
    // Check if this is a file drag from our FileTree
    const hasFileData = event.dataTransfer.types.includes('application/x-kurt-file')
    return hasFileData
  }

  const onDidDrop = (event) => {
    const { dataTransfer, position, group } = event
    const fileDataStr = dataTransfer.getData('application/x-kurt-file')

    if (!fileDataStr) return

    try {
      const fileData = JSON.parse(fileDataStr)
      const path = fileData.path

      // Determine position based on drop location
      let dropPosition
      if (group) {
        // Dropped on a group - add to that group
        dropPosition = { referenceGroup: group }
      } else if (position) {
        // Dropped to create a new split
        dropPosition = position
      } else {
        // Fallback to center group
        const centerGroup = centerGroupRef.current
        dropPosition = centerGroup
          ? { referenceGroup: centerGroup }
          : { direction: 'right', referencePanel: 'filetree' }
      }

      openFileAtPosition(path, dropPosition)
    } catch (e) {
      // Ignore parse errors
    }
  }

  return (
    <DockviewReact
      className="dockview-theme-abyss"
      components={components}
      onReady={onReady}
      showDndOverlay={showDndOverlay}
      onDidDrop={onDidDrop}
    />
  )
}
