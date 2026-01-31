import { useState, useEffect, useCallback, useRef } from 'react'
import { Play, Pause, Film, Code, RefreshCw, Plus, Trash2, GripVertical, AlertCircle, ChevronRight } from 'lucide-react'
import IntentToolbar from '../components/IntentToolbar'
import useFileWatch from '../hooks/useFileWatch'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

/**
 * Scene card in the sequence timeline.
 */
function SceneCard({ scene, index, isActive, onClick, onOpenScene }) {
  const isMC = scene.type === 'motion-canvas'
  const hasOutput = isMC ? scene.rendered_exists : scene.source_exists
  const label = scene.title || scene.id || `Scene ${index + 1}`
  const sublabel = isMC
    ? (scene.scene_path || 'No scene file')
    : (scene.source_path || 'No source file')

  return (
    <div
      className={`vs-scene-card ${isActive ? 'vs-scene-active' : ''} ${!hasOutput ? 'vs-scene-missing' : ''}`}
      onClick={() => onClick(index)}
    >
      <div className="vs-scene-grip">
        <GripVertical size={12} />
      </div>
      <div className="vs-scene-info">
        <div className="vs-scene-label">
          <span className={`vs-scene-type-badge ${isMC ? 'vs-badge-mc' : 'vs-badge-clip'}`}>
            {isMC ? 'MC' : 'Clip'}
          </span>
          <span className="vs-scene-name">{label}</span>
        </div>
        <div className="vs-scene-path">{sublabel}</div>
        {scene.trim_start != null && scene.trim_end != null && (
          <div className="vs-scene-trim">
            Trim: {scene.trim_start}s - {scene.trim_end}s
          </div>
        )}
      </div>
      {isMC && scene.scene_path && (
        <button
          type="button"
          className="vs-scene-open"
          onClick={(e) => { e.stopPropagation(); onOpenScene(scene.scene_path) }}
          title="Open scene source"
        >
          <Code size={12} />
        </button>
      )}
      {!hasOutput && (
        <span className="vs-scene-status" title="Output not yet rendered">
          <AlertCircle size={12} />
        </span>
      )}
    </div>
  )
}

/**
 * Transition indicator between scenes.
 */
function TransitionIndicator({ transition }) {
  if (!transition) return <div className="vs-transition vs-transition-cut"><ChevronRight size={10} /></div>

  return (
    <div className={`vs-transition vs-transition-${transition.type}`} title={`${transition.type} (${transition.duration}s)`}>
      <span className="vs-transition-label">{transition.type}</span>
      <span className="vs-transition-dur">{transition.duration}s</span>
    </div>
  )
}

/**
 * Video Sequence Panel - Multi-scene composition timeline using Motion Canvas.
 *
 * Displays a sequence of MC scenes and video clips that compose into a final video.
 * The agent manages the MC project (scene files, composition), renders the output.
 * This panel provides the timeline view and preview of the composed output.
 */
export default function VideoSequencePanel({ params }) {
  const {
    workflowId,
    pageId,
    pageConfig,
    onOpenFile,
  } = params || {}

  const [seqMeta, setSeqMeta] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeScene, setActiveScene] = useState(0)
  const videoRef = useRef(null)

  const { isStale, refresh, refreshKey } = useFileWatch(workflowId, pageId, {
    enabled: Boolean(workflowId && pageId),
  })

  const fetchData = useCallback(async () => {
    if (!workflowId || !pageId) return
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(
        apiUrl(`/api/workflows/${workflowId}/pages/${pageId}/data`)
      )
      if (!response.ok) throw new Error(`Failed to load: ${response.status}`)
      const data = await response.json()
      setSeqMeta(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [workflowId, pageId, refreshKey])

  useEffect(() => { fetchData() }, [fetchData])

  useEffect(() => {
    if (isStale) { fetchData(); refresh() }
  }, [isStale, fetchData, refresh])

  const handleRefresh = () => {
    fetchData()
    if (videoRef.current) videoRef.current.load()
  }

  const handleOpenScene = (scenePath) => {
    if (onOpenFile) onOpenFile(scenePath)
  }

  const scenes = seqMeta?.scenes || []
  const transitions = seqMeta?.transitions || []
  const hasOutput = seqMeta?.output_exists
  const outputUrl = hasOutput
    ? apiUrl(`/api/file/raw?path=${encodeURIComponent(seqMeta.output_path)}&v=${refreshKey}`)
    : null
  const resolution = seqMeta?.resolution || [1920, 1080]
  const title = pageConfig?.title || 'Video Sequence'
  const editable = pageConfig?.editable !== false

  // Find transition between scene i and i+1
  const getTransition = (idx) => {
    return transitions.find((t) =>
      (t.between && t.between[0] === idx && t.between[1] === idx + 1)
    )
  }

  return (
    <div className="panel-content vs-panel">
      <div className="vs-toolbar">
        <span className="vs-title">{title}</span>
        <div className="vs-toolbar-info">
          <span className="vs-scene-count">{scenes.length} scene{scenes.length !== 1 ? 's' : ''}</span>
          <span className="vs-resolution">{resolution[0]}x{resolution[1]}</span>
        </div>
        <div className="vs-toolbar-actions">
          <button type="button" className="vs-btn" onClick={handleRefresh} title="Refresh">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {editable && (
        <IntentToolbar
          workflowId={workflowId}
          pageId={pageId}
          pageType="video-sequence"
          onRefresh={handleRefresh}
        />
      )}

      {error && <div className="vs-error"><AlertCircle size={14} /> {error}</div>}

      {isLoading ? (
        <div className="vs-loading">Loading sequence...</div>
      ) : (
        <div className="vs-content">
          {/* Preview area */}
          <div className="vs-preview">
            {hasOutput ? (
              <video
                ref={videoRef}
                src={outputUrl}
                className="vs-video"
                controls
              />
            ) : (
              <div className="vs-preview-placeholder">
                <Film size={48} />
                <p>No composed output yet</p>
                <p className="vs-preview-hint">
                  {scenes.length > 0
                    ? 'The agent will render the sequence when all scenes are ready.'
                    : 'Add scenes to begin composing a video.'}
                </p>
              </div>
            )}
          </div>

          {/* Scene timeline */}
          <div className="vs-timeline">
            <div className="vs-timeline-header">
              <span className="vs-timeline-label">Scenes</span>
            </div>
            <div className="vs-scene-list">
              {scenes.length === 0 ? (
                <div className="vs-empty">No scenes defined in workflow.</div>
              ) : (
                scenes.map((scene, idx) => (
                  <div key={scene.id || idx} className="vs-scene-row">
                    <SceneCard
                      scene={scene}
                      index={idx}
                      isActive={activeScene === idx}
                      onClick={setActiveScene}
                      onOpenScene={handleOpenScene}
                    />
                    {idx < scenes.length - 1 && (
                      <TransitionIndicator transition={getTransition(idx)} />
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
