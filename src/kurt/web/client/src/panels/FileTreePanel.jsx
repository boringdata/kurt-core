import React, { useState, useRef } from 'react'
import FileTree from '../components/FileTree'

export default function FileTreePanel({ params }) {
  const { onOpenFile, onOpenFileToSide, projectRoot, activeFile, collapsed, onToggleCollapse } = params
  const [creatingFile, setCreatingFile] = useState(false)
  const fileTreeRef = useRef(null)

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
        <div className="sidebar-collapsed-label">Files</div>
      </div>
    )
  }

  return (
    <div className="panel-content filetree-panel">
      <div className="sidebar-header">
        <span className="sidebar-title">Files</span>
        <div className="sidebar-header-actions">
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
      <FileTree
        ref={fileTreeRef}
        onOpen={onOpenFile}
        onOpenToSide={onOpenFileToSide}
        projectRoot={projectRoot}
        activeFile={activeFile}
        creatingFile={creatingFile}
        onFileCreated={handleFileCreated}
        onCancelCreate={handleCancelCreate}
      />
    </div>
  )
}
