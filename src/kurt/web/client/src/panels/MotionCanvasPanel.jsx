import { useState, useEffect, useCallback, useRef } from 'react'
import { Play, Pause, SkipBack, SkipForward, RefreshCw, Settings, Code, AlertCircle } from 'lucide-react'
import IntentToolbar from '../components/IntentToolbar'
import useFileWatch from '../hooks/useFileWatch'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

/**
 * Motion Canvas Panel - Rendered output viewer with agent-as-editor model.
 *
 * Displays rendered Motion Canvas output (video or iframe preview).
 * The agent edits .tsx scene files; this panel is the viewer.
 * IntentToolbar captures user editing intent and dispatches to agent.
 */
export default function MotionCanvasPanel({ params }) {
  const {
    workflowId,
    pageId,
    pageConfig,
    onOpenFile,
  } = params || {}

  const [sceneMeta, setSceneMeta] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showSettings, setShowSettings] = useState(false)
  const [previewScale, setPreviewScale] = useState(1)
  const videoRef = useRef(null)
  const iframeRef = useRef(null)
  const previewRef = useRef(null)

  // File watch for auto-refresh after agent edits
  const { isStale, refresh, refreshKey } = useFileWatch(workflowId, pageId, {
    enabled: Boolean(workflowId && pageId),
  })

  const fetchSceneData = useCallback(async () => {
    if (!workflowId || !pageId) return
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(
        apiUrl(`/api/workflows/${workflowId}/pages/${pageId}/data`)
      )
      if (!response.ok) throw new Error(`Failed to load: ${response.status}`)
      const data = await response.json()
      setSceneMeta(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [workflowId, pageId, refreshKey])

  useEffect(() => {
    fetchSceneData()
  }, [fetchSceneData])

  // Auto-refresh when file changes detected
  useEffect(() => {
    if (isStale) {
      fetchSceneData()
      refresh()
    }
  }, [isStale, fetchSceneData, refresh])

  const handleOpenScene = () => {
    if (sceneMeta?.scene_path && onOpenFile) {
      onOpenFile(sceneMeta.scene_path)
    }
  }

  const handleRefresh = () => {
    fetchSceneData()
    // Also reload video/iframe
    if (videoRef.current) {
      videoRef.current.load()
    }
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src
    }
  }

  // Determine render mode: iframe (live preview) > video (rendered output) > placeholder
  const hasLivePreview = sceneMeta?.preview_url
  const hasRenderedOutput = sceneMeta?.output_path && sceneMeta?.output_exists
  const outputUrl = hasRenderedOutput
    ? apiUrl(`/api/file/raw?path=${encodeURIComponent(sceneMeta.output_path)}&v=${refreshKey}`)
    : null

  const title = pageConfig?.title || 'Motion Canvas'
  const editable = pageConfig?.editable !== false

  return (
    <div className="panel-content mc-panel">
      <div className="mc-toolbar">
        <span className="mc-title">{title}</span>
        <div className="mc-toolbar-actions">
          <button type="button" className="mc-btn" onClick={handleRefresh} title="Refresh preview">
            <RefreshCw size={14} />
          </button>
          {sceneMeta?.scene_path && (
            <button type="button" className="mc-btn" onClick={handleOpenScene} title="Open scene source">
              <Code size={14} />
            </button>
          )}
          <button
            type="button"
            className={`mc-btn ${showSettings ? 'mc-btn-active' : ''}`}
            onClick={() => setShowSettings(!showSettings)}
            title="Settings"
          >
            <Settings size={14} />
          </button>
        </div>
      </div>

      {showSettings && (
        <div className="mc-settings">
          <label className="mc-setting">
            <span>Scale:</span>
            <select
              value={previewScale}
              onChange={(e) => setPreviewScale(Number(e.target.value))}
              className="mc-setting-select"
            >
              <option value={0.5}>50%</option>
              <option value={1}>100%</option>
              <option value={2}>200%</option>
            </select>
          </label>
          {sceneMeta?.duration && (
            <span className="mc-setting-info">Duration: {sceneMeta.duration}s</span>
          )}
          {sceneMeta?.fps && (
            <span className="mc-setting-info">FPS: {sceneMeta.fps}</span>
          )}
        </div>
      )}

      {/* Intent toolbar for agent-dispatched editing */}
      {editable && (
        <IntentToolbar
          workflowId={workflowId}
          pageId={pageId}
          pageType="motion-canvas"
          onRefresh={handleRefresh}
        />
      )}

      {error && <div className="mc-error"><AlertCircle size={14} /> {error}</div>}

      {isLoading ? (
        <div className="mc-loading">Loading scene...</div>
      ) : (
        <div
          ref={previewRef}
          className="mc-preview-area"
        >
          {hasLivePreview ? (
            /* Mode 1: Live preview via Motion Canvas dev server iframe */
            <div className="mc-iframe-container" style={{ transform: `scale(${previewScale})`, transformOrigin: 'top left' }}>
              <iframe
                ref={iframeRef}
                src={sceneMeta.preview_url}
                className="mc-iframe"
                title="Motion Canvas Preview"
                sandbox="allow-scripts allow-same-origin"
              />
            </div>
          ) : hasRenderedOutput ? (
            /* Mode 2: Rendered output video */
            <div className="mc-video-container" style={{ transform: `scale(${previewScale})`, transformOrigin: 'center center' }}>
              <video
                ref={videoRef}
                src={outputUrl}
                className="mc-video"
                controls
                loop
              />
            </div>
          ) : (
            /* Mode 3: No output yet - show scene info */
            <div className="mc-placeholder">
              <div className="mc-placeholder-icon">
                <Code size={48} />
              </div>
              <div className="mc-placeholder-text">
                {sceneMeta?.exists ? (
                  <>
                    <p>Scene file found: <code>{sceneMeta.scene_path}</code></p>
                    <p className="mc-placeholder-hint">
                      No rendered output yet. The agent will render the scene
                      when the workflow runs, or you can use the intent toolbar
                      to request edits.
                    </p>
                  </>
                ) : (
                  <>
                    <p>Scene file not found</p>
                    {sceneMeta?.scene_path && (
                      <p className="mc-placeholder-hint">Expected at: <code>{sceneMeta.scene_path}</code></p>
                    )}
                  </>
                )}
              </div>
              {sceneMeta?.scene_path && (
                <button type="button" className="mc-open-source-btn" onClick={handleOpenScene}>
                  <Code size={14} /> Open Scene Source
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
