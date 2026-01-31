import { useState, useEffect, useCallback, useRef } from 'react'
import { ZoomIn, ZoomOut, RotateCw, Download, Maximize2, Pen, Undo2, Redo2, RefreshCw, AlertCircle } from 'lucide-react'
import IntentToolbar from '../components/IntentToolbar'
import useFileWatch from '../hooks/useFileWatch'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

const MIN_ZOOM = 0.1
const MAX_ZOOM = 5
const ZOOM_STEP = 0.25

/**
 * Image Viewer Panel - View images with zoom/rotate/annotate and agent-as-editor.
 *
 * When editable, includes IntentToolbar for dispatching text/shape overlay
 * intents to the agent (which uses ImageMagick/Pillow to edit the image).
 * Also supports manual annotation drawing for quick markup.
 */
export default function ImageViewerPanel({ params }) {
  const {
    workflowId,
    pageId,
    pageConfig,
  } = params || {}

  const [imageUrl, setImageUrl] = useState(null)
  const [imageMeta, setImageMeta] = useState(null)
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [fitMode, setFitMode] = useState('contain')
  const [annotating, setAnnotating] = useState(false)
  const [annotations, setAnnotations] = useState([])
  const [undoStack, setUndoStack] = useState([])
  const [currentPath, setCurrentPath] = useState([])
  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  const imgRef = useRef(null)
  const isDrawing = useRef(false)

  const editable = pageConfig?.editable !== false

  // File watch for auto-refresh after agent edits
  const { isStale, refresh, refreshKey } = useFileWatch(workflowId, pageId, {
    enabled: Boolean(workflowId && pageId),
  })

  const fetchImageData = useCallback(async () => {
    if (!workflowId || !pageId) return
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(
        apiUrl(`/api/workflows/${workflowId}/pages/${pageId}/data`)
      )
      if (!response.ok) throw new Error(`Failed to load: ${response.status}`)
      const data = await response.json()
      setImageMeta(data)

      if (data.image_path && data.exists) {
        setImageUrl(apiUrl(`/api/file/raw?path=${encodeURIComponent(data.image_path)}&v=${refreshKey}`))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [workflowId, pageId, refreshKey])

  useEffect(() => {
    fetchImageData()
  }, [fetchImageData])

  // Auto-refresh when file changes detected
  useEffect(() => {
    if (isStale) {
      fetchImageData()
      refresh()
    }
  }, [isStale, fetchImageData, refresh])

  const handleRefresh = () => fetchImageData()

  const handleZoomIn = () => setZoom((z) => Math.min(z + ZOOM_STEP, MAX_ZOOM))
  const handleZoomOut = () => setZoom((z) => Math.max(z - ZOOM_STEP, MIN_ZOOM))
  const handleRotate = () => setRotation((r) => (r + 90) % 360)

  const handleFitToggle = () => {
    if (fitMode === 'contain') {
      setFitMode('actual')
      setZoom(1)
    } else {
      setFitMode('contain')
      setZoom(1)
    }
  }

  const handleDownload = () => {
    if (!imageUrl) return
    const a = document.createElement('a')
    a.href = imageUrl
    a.download = imageMeta?.image_path?.split('/').pop() || 'image'
    a.click()
  }

  const handleWheel = useCallback((e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault()
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
      setZoom((z) => Math.max(MIN_ZOOM, Math.min(z + delta, MAX_ZOOM)))
    }
  }, [])

  // Annotation drawing
  const startDrawing = (e) => {
    if (!annotating) return
    isDrawing.current = true
    const rect = canvasRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    setCurrentPath([{ x, y }])
  }

  const draw = (e) => {
    if (!isDrawing.current || !annotating) return
    const rect = canvasRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    setCurrentPath((prev) => [...prev, { x, y }])
  }

  const endDrawing = () => {
    if (!isDrawing.current) return
    isDrawing.current = false
    if (currentPath.length > 1) {
      setAnnotations((prev) => [...prev, currentPath])
      setUndoStack([])
    }
    setCurrentPath([])
  }

  const handleUndo = () => {
    if (annotations.length === 0) return
    const last = annotations[annotations.length - 1]
    setAnnotations((prev) => prev.slice(0, -1))
    setUndoStack((prev) => [...prev, last])
  }

  const handleRedo = () => {
    if (undoStack.length === 0) return
    const last = undoStack[undoStack.length - 1]
    setUndoStack((prev) => prev.slice(0, -1))
    setAnnotations((prev) => [...prev, last])
  }

  // Draw annotations on canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const img = imgRef.current
    if (!img || !img.naturalWidth) return

    canvas.width = img.naturalWidth
    canvas.height = img.naturalHeight
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    ctx.strokeStyle = '#ff4444'
    ctx.lineWidth = 3
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    const scaleX = img.naturalWidth / (img.clientWidth || 1)
    const scaleY = img.naturalHeight / (img.clientHeight || 1)

    const drawPath = (path) => {
      if (path.length < 2) return
      ctx.beginPath()
      ctx.moveTo(path[0].x * scaleX, path[0].y * scaleY)
      for (let i = 1; i < path.length; i++) {
        ctx.lineTo(path[i].x * scaleX, path[i].y * scaleY)
      }
      ctx.stroke()
    }

    annotations.forEach(drawPath)
    if (currentPath.length > 1) drawPath(currentPath)
  }, [annotations, currentPath])

  const title = pageConfig?.title || 'Image Viewer'

  return (
    <div className="panel-content iv-panel">
      <div className="iv-toolbar">
        <span className="iv-title">{title}</span>
        <div className="iv-toolbar-actions">
          <button type="button" className="iv-btn" onClick={handleRefresh} title="Refresh">
            <RefreshCw size={14} />
          </button>
          <button type="button" className="iv-btn" onClick={handleZoomOut} title="Zoom out">
            <ZoomOut size={14} />
          </button>
          <span className="iv-zoom-label">{Math.round(zoom * 100)}%</span>
          <button type="button" className="iv-btn" onClick={handleZoomIn} title="Zoom in">
            <ZoomIn size={14} />
          </button>
          <div className="iv-separator" />
          <button type="button" className="iv-btn" onClick={handleRotate} title="Rotate 90deg">
            <RotateCw size={14} />
          </button>
          <button
            type="button"
            className={`iv-btn ${fitMode === 'actual' ? 'iv-btn-active' : ''}`}
            onClick={handleFitToggle}
            title={fitMode === 'contain' ? 'Actual size' : 'Fit to view'}
          >
            <Maximize2 size={14} />
          </button>
          {editable && (
            <>
              <div className="iv-separator" />
              <button
                type="button"
                className={`iv-btn ${annotating ? 'iv-btn-active' : ''}`}
                onClick={() => setAnnotating(!annotating)}
                title="Annotate"
              >
                <Pen size={14} />
              </button>
              {annotating && (
                <>
                  <button type="button" className="iv-btn" onClick={handleUndo} title="Undo" disabled={annotations.length === 0}>
                    <Undo2 size={14} />
                  </button>
                  <button type="button" className="iv-btn" onClick={handleRedo} title="Redo" disabled={undoStack.length === 0}>
                    <Redo2 size={14} />
                  </button>
                </>
              )}
            </>
          )}
          <div className="iv-separator" />
          <button type="button" className="iv-btn" onClick={handleDownload} title="Download">
            <Download size={14} />
          </button>
        </div>
      </div>

      {/* Intent toolbar for text/shape overlays (agent-dispatched) */}
      {editable && (
        <IntentToolbar
          workflowId={workflowId}
          pageId={pageId}
          pageType="image"
          onRefresh={handleRefresh}
        />
      )}

      {error && <div className="iv-error"><AlertCircle size={14} /> {error}</div>}

      {isLoading ? (
        <div className="iv-loading">Loading image...</div>
      ) : !imageUrl ? (
        <div className="iv-empty">
          <div className="iv-empty-icon">No image available</div>
          {imageMeta?.image_path && (
            <div className="iv-empty-path">Expected at: {imageMeta.image_path}</div>
          )}
        </div>
      ) : (
        <div
          ref={containerRef}
          className={`iv-container ${annotating ? 'iv-annotating' : ''}`}
          onWheel={handleWheel}
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={endDrawing}
          onMouseLeave={endDrawing}
        >
          <div
            className="iv-image-wrapper"
            style={{
              transform: `scale(${zoom}) rotate(${rotation}deg)`,
              transformOrigin: 'center center',
            }}
          >
            <img
              ref={imgRef}
              src={imageUrl}
              alt={title}
              className={`iv-image ${fitMode === 'contain' ? 'iv-fit-contain' : 'iv-fit-actual'}`}
              draggable={false}
            />
            {annotating && (
              <canvas
                ref={canvasRef}
                className="iv-annotation-canvas"
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
