import React, { useState, useEffect, useRef, useCallback } from 'react'
import ImageEditor from '../components/ImageEditor'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

// Check if file is an image
const isImageFile = (filepath) => {
  if (!filepath) return false
  const ext = filepath.split('.').pop()?.toLowerCase()
  return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'avif', 'tiff', 'bmp'].includes(ext)
}

export default function ImageEditorPanel({ params: initialParams, api }) {
  const [params, setParams] = useState(initialParams || {})
  const [imageSrc, setImageSrc] = useState(null)
  const [error, setError] = useState(null)
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })

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

  // Load image from file path or URL
  useEffect(() => {
    if (url) {
      setImageSrc(url)
      setError(null)
      return
    }

    if (!path) {
      setImageSrc(null)
      return
    }

    if (!isImageFile(path)) {
      setError('Not an image file')
      setImageSrc(null)
      return
    }

    // Load image via API (convert to data URL)
    const loadImage = async () => {
      try {
        // For local files, we need to fetch as binary and create a blob URL
        const response = await fetch(apiUrl(`/api/file?path=${encodeURIComponent(path)}`))
        if (!response.ok) {
          throw new Error('Failed to load file')
        }

        // Check if it's actually binary image data or text
        const contentType = response.headers.get('content-type')
        if (contentType?.includes('application/json')) {
          // The API returns JSON with content - we need to handle this differently
          // For now, construct a file URL
          setImageSrc(`${apiBase}/api/file/raw?path=${encodeURIComponent(path)}`)
        } else {
          const blob = await response.blob()
          const url = URL.createObjectURL(blob)
          setImageSrc(url)
        }
        setError(null)
      } catch (err) {
        setError(err.message)
        setImageSrc(null)
      }
    }

    loadImage()
  }, [path, url])

  // Track container size for responsive canvas
  useEffect(() => {
    if (!containerRef.current) return

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        setDimensions({
          width: Math.max(400, width - 20),
          height: Math.max(300, height - 80), // Account for toolbar
        })
      }
    })

    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  const handleSave = useCallback(async (dataUrl) => {
    // Convert data URL to blob and save
    // This would need backend support for saving binary files
    console.log('Save not implemented yet')
  }, [path])

  const handleGenerate = useCallback((generatedUrl) => {
    setImageSrc(generatedUrl)
  }, [])

  return (
    <div className="panel-content image-editor-panel" ref={containerRef}>
      {error && (
        <div className="panel-error">
          {error}
        </div>
      )}

      {!imageSrc && !error && (
        <div className="panel-empty">
          <div className="empty-state">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor" opacity="0.3">
              <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" />
            </svg>
            <p>No image loaded</p>
            <p className="hint">Open an image file or use AI Generate to create one</p>
          </div>
        </div>
      )}

      <ImageEditor
        imageSrc={imageSrc}
        onSave={handleSave}
        onGenerate={handleGenerate}
        width={dimensions.width}
        height={dimensions.height}
      />
    </div>
  )
}
