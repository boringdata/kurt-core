import React, { useState } from 'react'
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
          <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
            <path d="M6 3.5L10.5 8L6 12.5V3.5Z" />
          </svg>
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
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
              <path d="M1.5 1h3l.5.5v2h9l.5.5v10l-.5.5h-12l-.5-.5v-12l.5-.5zm0 3.5V13h11V4H5l-.5-.5V2H2v2.5z"/>
            </svg>
          </button>
          <button
            type="button"
            className={`view-toggle-btn ${viewMode === 'changes' ? 'active' : ''}`}
            onClick={() => setViewMode('changes')}
            title="Git changes"
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
              <path d="M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.5a.5.5 0 0 1 0-1h3.57a4.002 4.002 0 0 1 7.86 0h3.57a.5.5 0 0 1 0 1h-3.57zM8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/>
            </svg>
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
              <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                <path d="M9.5 1.1l3.4 3.5c.2.2.1.4.1.4v8c0 .6-.4 1-1 1H4c-.6 0-1-.4-1-1V2c0-.5.4-1 1-1h5.5zM9 2H4v12h8V5.5L9 2zm.5 3V2l3 3h-3z"/>
                <path d="M8 7v2H6v1h2v2h1v-2h2V9H9V7H8z"/>
              </svg>
            </button>
          )}
          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={onToggleCollapse}
            title="Collapse file tree"
            aria-label="Collapse file tree"
          >
            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
              <path d="M10 3.5L5.5 8L10 12.5V3.5Z" />
            </svg>
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
