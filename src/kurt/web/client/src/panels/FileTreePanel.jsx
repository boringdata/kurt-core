import React from 'react'
import FileTree from '../components/FileTree'

export default function FileTreePanel({ params }) {
  const { onOpenFile, onOpenFileToSide, projectRoot, activeFile } = params

  return (
    <div className="panel-content filetree-panel">
      <FileTree
        onOpen={onOpenFile}
        onOpenToSide={onOpenFileToSide}
        projectRoot={projectRoot}
        activeFile={activeFile}
      />
    </div>
  )
}
