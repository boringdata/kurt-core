import React, { useState, useEffect, useRef } from 'react'
import VideoEditor from '../components/VideoEditor'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

// Check if file is a video
const isVideoFile = (filepath) => {
  if (!filepath) return false
  const ext = filepath.split('.').pop()?.toLowerCase()
  return ['mp4', 'webm', 'mov', 'avi', 'mkv', 'ogg', 'm4v'].includes(ext)
}

export default function VideoEditorPanel({ params: initialParams, api }) {
  const [params, setParams] = useState(initialParams || {})
  const [videoSrc, setVideoSrc] = useState(null)
  const [error, setError] = useState(null)

  // Track params updates from dockview
  useEffect(() => {
    if (!api) return
    const disposable = api.onDidParametersChange((event) => {
      if (event.params) {
        setParams((prev) => ({ ...prev, ...event.params }))
      }
    })
    return () => disposable.dispose()
  }, [api])

  const { path, url } = params || {}

  // Load video from file path or URL
  useEffect(() => {
    if (url) {
      setVideoSrc(url)
      setError(null)
      return
    }

    if (!path) {
      setVideoSrc(null)
      return
    }

    if (!isVideoFile(path)) {
      setError('Not a video file')
      setVideoSrc(null)
      return
    }

    // For videos, we can use a direct file URL or raw endpoint
    // This assumes the backend can serve raw files
    setVideoSrc(`${apiBase}/api/file/raw?path=${encodeURIComponent(path)}`)
    setError(null)
  }, [path, url])

  const handleSave = (outputPath) => {
    console.log('Video saved to:', outputPath)
  }

  const handleGenerate = (generatedUrl) => {
    setVideoSrc(generatedUrl)
  }

  return (
    <div className="panel-content video-editor-panel">
      {error && (
        <div className="panel-error">
          {error}
        </div>
      )}

      {!videoSrc && !error && (
        <div className="panel-empty">
          <div className="empty-state">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor" opacity="0.3">
              <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z" />
            </svg>
            <p>No video loaded</p>
            <p className="hint">Open a video file or use AI Generate to create one</p>
          </div>
        </div>
      )}

      <VideoEditor
        videoSrc={videoSrc}
        filePath={path}
        onSave={handleSave}
        onGenerate={handleGenerate}
      />
    </div>
  )
}
