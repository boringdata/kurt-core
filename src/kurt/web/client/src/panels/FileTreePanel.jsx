import React from 'react'
import FileTree from '../components/FileTree'

export default function FileTreePanel({ params }) {
  const { onOpenFile, onOpenFileToSide, projectRoot, activeFile, collapsed, onToggleCollapse } = params

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
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
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
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={onToggleCollapse}
          title="Collapse file tree"
          aria-label="Collapse file tree"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M10 3.5L5.5 8L10 12.5V3.5Z" />
          </svg>
        </button>
      </div>
      <FileTree
        onOpen={onOpenFile}
        onOpenToSide={onOpenFileToSide}
        projectRoot={projectRoot}
        activeFile={activeFile}
      />
    </div>
  )
}
