import React, { useState } from 'react'
import { ChevronRight, ChevronLeft, FolderOpen, GitBranch, Plus } from 'lucide-react'
import FileTree from '../components/FileTree'
import GitChangesView from '../components/GitChangesView'

export default function FileTreePanel({ params }) {
  const { onOpenFile, onOpenFileToSide, onOpenDiff, projectRoot, activeFile, activeDiffFile, collapsed, onToggleCollapse } = params
  const [creatingFile, setCreatingFile] = useState(false)
  const [viewMode, setViewMode] = useState('files') // 'files' | 'changes'

  const handleNewFile = () => {
    setCreatingFile(true)
  }

  const handleFileCreated = (path) => {
    setCreatingFile(false)
    if (path) {
      onOpenFile(path)
    }
  }

  const handleCancelCreate = () => {
    setCreatingFile(false)
  }

  if (collapsed) {
    return (
      <div className="panel-content filetree-panel filetree-collapsed">
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={onToggleCollapse}
          title="Expand file tree"
          aria-label="Expand file tree"
        >
          <ChevronRight size={12} />
        </button>
        <div className="sidebar-collapsed-label">{viewMode === 'files' ? 'Files' : 'Changes'}</div>
      </div>
    )
  }

  return (
    <div className="panel-content filetree-panel">
      <div className="sidebar-header">
        <div className="sidebar-view-toggle">
          <button
            type="button"
            className={`view-toggle-btn ${viewMode === 'files' ? 'active' : ''}`}
            onClick={() => setViewMode('files')}
            title="File tree"
          >
            <FolderOpen size={14} />
          </button>
          <button
            type="button"
            className={`view-toggle-btn ${viewMode === 'changes' ? 'active' : ''}`}
            onClick={() => setViewMode('changes')}
            title="Git changes"
          >
            <GitBranch size={14} />
          </button>
        </div>
        <div className="sidebar-header-actions">
          {viewMode === 'files' && (
            <button
              type="button"
              className="sidebar-action-btn"
              onClick={handleNewFile}
              title="New File"
              aria-label="New File"
            >
              <Plus size={14} />
            </button>
          )}
          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={onToggleCollapse}
            title="Collapse file tree"
            aria-label="Collapse file tree"
          >
            <ChevronLeft size={12} />
          </button>
        </div>
      </div>
      {viewMode === 'files' ? (
        <FileTree
          onOpen={onOpenFile}
          onOpenToSide={onOpenFileToSide}
          projectRoot={projectRoot}
          activeFile={activeFile}
          creatingFile={creatingFile}
          onFileCreated={handleFileCreated}
          onCancelCreate={handleCancelCreate}
        />
      ) : (
        <GitChangesView
          onOpenDiff={onOpenDiff}
          activeDiffFile={activeDiffFile}
        />
      )}
    </div>
  )
}
