import React, { useState, useEffect } from 'react'
import FileTree from './components/FileTree'
import Editor from './components/Editor'

export default function App() {
  const [currentPath, setCurrentPath] = useState(null)
  const [content, setContent] = useState('')

  useEffect(() => {
    if (currentPath) {
      fetch(`/api/file?path=${encodeURIComponent(currentPath)}`)
        .then((r) => r.json())
        .then((data) => setContent(data.content))
        .catch(() => setContent(''))
    }
  }, [currentPath])

  const save = async (newContent) => {
    if (!currentPath) return
    await fetch(`/api/file?path=${encodeURIComponent(currentPath)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: newContent }),
    })
  }

  return (
    <div className="app">
      <div className="sidebar">
        <FileTree onOpen={(p) => setCurrentPath(p)} />
      </div>
      <div className="editor">
        <Editor content={content} onSave={save} />
      </div>
    </div>
  )
}
