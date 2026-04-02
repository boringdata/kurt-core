import { useState, useEffect, useCallback, useRef } from 'react'
import { Play, Pause, Scissors, SkipBack, SkipForward, Volume2, VolumeX, Download, RotateCw, Trash2, RefreshCw, AlertCircle, Send } from 'lucide-react'
import IntentToolbar from '../components/IntentToolbar'
import useFileWatch from '../hooks/useFileWatch'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

function TrimHandle({ position, side, onDrag }) {
  const handleRef = useRef(null)
  const dragging = useRef(false)

  const handleMouseDown = (e) => {
    e.preventDefault()
    e.stopPropagation()
    dragging.current = true

    const startX = e.clientX
    const startPos = position

    const onMouseMove = (e) => {
      if (!dragging.current) return
      const parent = handleRef.current?.parentElement
      if (!parent) return
      const rect = parent.getBoundingClientRect()
      const delta = (e.clientX - startX) / rect.width
      onDrag(Math.max(0, Math.min(1, startPos + delta)))
    }

    const onMouseUp = () => {
      dragging.current = false
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  }

  return (
    <div
      ref={handleRef}
      className={`ve-trim-handle ve-trim-${side}`}
      style={{ left: `${position * 100}%` }}
      onMouseDown={handleMouseDown}
      role="slider"
      tabIndex={0}
      aria-label={`${side} trim point`}
      aria-valuenow={Math.round(position * 100)}
    />
  )
}

/**
 * Video Editor Panel - Viewer with trim/cut and agent-as-editor intent capture.
 *
 * The agent handles actual video editing (ffmpeg commands).
 * This panel is a viewer with trim/cut UI and IntentToolbar for text/shape overlays.
 */
export default function VideoEditorPanel({ params }) {
  const {
    workflowId,
    pageId,
    pageConfig,
  } = params || {}

  const [videoMeta, setVideoMeta] = useState(null)
  const [videoUrl, setVideoUrl] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [trimStart, setTrimStart] = useState(0)
  const [trimEnd, setTrimEnd] = useState(1)
  const [isTrimming, setIsTrimming] = useState(false)
  const [trimSegments, setTrimSegments] = useState([])
  const [isApplyingTrim, setIsApplyingTrim] = useState(false)
  const videoRef = useRef(null)

  const canTrim = pageConfig?.trim !== false
  const editable = pageConfig?.editable !== false

  // File watch for auto-refresh after agent edits
  const { isStale, refresh, refreshKey } = useFileWatch(workflowId, pageId, {
    enabled: Boolean(workflowId && pageId),
  })

  const fetchVideoData = useCallback(async () => {
    if (!workflowId || !pageId) return
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(
        apiUrl(`/api/workflows/${workflowId}/pages/${pageId}/data`)
      )
      if (!response.ok) throw new Error(`Failed to load: ${response.status}`)
      const data = await response.json()
      setVideoMeta(data)

      if (data.video_path && data.exists) {
        setVideoUrl(apiUrl(`/api/file/raw?path=${encodeURIComponent(data.video_path)}&v=${refreshKey}`))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [workflowId, pageId, refreshKey])

  useEffect(() => {
    fetchVideoData()
  }, [fetchVideoData])

  // Auto-refresh when file changes detected
  useEffect(() => {
    if (isStale) {
      fetchVideoData()
      refresh()
    }
  }, [isStale, fetchVideoData, refresh])

  // Sync video element time updates
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const onTimeUpdate = () => {
      setCurrentTime(video.currentTime)
      if (isTrimming && video.currentTime >= trimEnd * duration) {
        video.pause()
        setIsPlaying(false)
      }
    }
    const onLoaded = () => setDuration(video.duration)
    const onEnded = () => setIsPlaying(false)

    video.addEventListener('timeupdate', onTimeUpdate)
    video.addEventListener('loadedmetadata', onLoaded)
    video.addEventListener('ended', onEnded)

    return () => {
      video.removeEventListener('timeupdate', onTimeUpdate)
      video.removeEventListener('loadedmetadata', onLoaded)
      video.removeEventListener('ended', onEnded)
    }
  }, [duration, isTrimming, trimEnd])

  const handlePlayPause = () => {
    const video = videoRef.current
    if (!video) return
    if (isPlaying) {
      video.pause()
    } else {
      if (isTrimming && currentTime < trimStart * duration) {
        video.currentTime = trimStart * duration
      }
      video.play()
    }
    setIsPlaying(!isPlaying)
  }

  const handleSeek = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const progress = x / rect.width
    const newTime = progress * duration
    if (videoRef.current) videoRef.current.currentTime = newTime
    setCurrentTime(newTime)
  }

  const handleSkipBack = () => {
    if (videoRef.current) videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime - 5)
  }

  const handleSkipForward = () => {
    if (videoRef.current) videoRef.current.currentTime = Math.min(duration, videoRef.current.currentTime + 5)
  }

  const handleVolumeChange = (e) => {
    const vol = Number(e.target.value)
    setVolume(vol)
    if (videoRef.current) videoRef.current.volume = vol
    setIsMuted(vol === 0)
  }

  const handleToggleMute = () => {
    if (videoRef.current) videoRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const handleTrimStartChange = (pos) => setTrimStart(Math.min(pos, trimEnd - 0.01))
  const handleTrimEndChange = (pos) => setTrimEnd(Math.max(pos, trimStart + 0.01))

  const handleAddTrimCut = () => {
    if (!duration) return
    const cutPoint = currentTime / duration
    const segStart = Math.max(0, cutPoint - 0.005)
    const segEnd = Math.min(1, cutPoint + 0.005)
    setTrimSegments((prev) => [...prev, { start: segStart, end: segEnd }])
  }

  const handleRemoveSegment = (idx) => {
    setTrimSegments((prev) => prev.filter((_, i) => i !== idx))
  }

  // Dispatch trim/cut edits to the agent
  const handleApplyTrim = async () => {
    if (!workflowId || !pageId) return
    setIsApplyingTrim(true)
    try {
      const intents = []
      if (trimStart > 0 || trimEnd < 1) {
        intents.push({
          action: 'trim',
          time_range: { start: trimStart * duration, end: trimEnd * duration },
        })
      }
      for (const seg of trimSegments) {
        intents.push({
          action: 'cut',
          time_range: { start: seg.start * duration, end: seg.end * duration },
        })
      }
      if (intents.length === 0) return

      const res = await fetch(
        apiUrl(`/api/workflows/${workflowId}/pages/${pageId}/edit`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ intents }),
        }
      )
      if (!res.ok) throw new Error(`Dispatch failed: ${res.status}`)
      setIsTrimming(false)
      setTrimStart(0)
      setTrimEnd(1)
      setTrimSegments([])
    } catch (err) {
      console.error('Trim dispatch failed:', err)
    } finally {
      setIsApplyingTrim(false)
    }
  }

  const handleDownload = () => {
    if (!videoUrl) return
    const a = document.createElement('a')
    a.href = videoUrl
    a.download = videoMeta?.video_path?.split('/').pop() || 'video.mp4'
    a.click()
  }

  const handleRefresh = () => {
    fetchVideoData()
    if (videoRef.current) videoRef.current.load()
  }

  const formatTime = (t) => {
    if (!t || isNaN(t)) return '0:00'
    const mins = Math.floor(t / 60)
    const secs = Math.floor(t % 60)
    return `${mins}:${String(secs).padStart(2, '0')}`
  }

  const title = pageConfig?.title || 'Video'

  return (
    <div className="panel-content ve-panel">
      <div className="ve-toolbar">
        <span className="ve-title">{title}</span>
        <div className="ve-toolbar-actions">
          <button type="button" className="ve-btn" onClick={handleRefresh} title="Refresh">
            <RefreshCw size={14} />
          </button>
          {canTrim && (
            <button
              type="button"
              className={`ve-btn ${isTrimming ? 've-btn-active' : ''}`}
              onClick={() => setIsTrimming(!isTrimming)}
              title="Toggle trim mode"
            >
              <Scissors size={14} /> Trim
            </button>
          )}
          <button type="button" className="ve-btn" onClick={handleDownload} title="Download video">
            <Download size={14} />
          </button>
        </div>
      </div>

      {/* Intent toolbar for text/shape overlays */}
      {editable && (
        <IntentToolbar
          workflowId={workflowId}
          pageId={pageId}
          pageType="video"
          onRefresh={handleRefresh}
        />
      )}

      {error && <div className="ve-error"><AlertCircle size={14} /> {error}</div>}

      {isLoading ? (
        <div className="ve-loading">Loading video...</div>
      ) : !videoUrl ? (
        <div className="ve-empty">
          <div className="ve-empty-text">No video available</div>
          {videoMeta?.video_path && (
            <div className="ve-empty-path">Expected at: {videoMeta.video_path}</div>
          )}
        </div>
      ) : (
        <>
          <div className="ve-video-container">
            <video
              ref={videoRef}
              src={videoUrl}
              className="ve-video"
              onClick={handlePlayPause}
              volume={isMuted ? 0 : volume}
            />
          </div>

          <div className="ve-controls">
            <div className="ve-transport">
              <button type="button" className="ve-transport-btn" onClick={handleSkipBack} title="Back 5s">
                <SkipBack size={14} />
              </button>
              <button type="button" className="ve-transport-btn ve-play-btn" onClick={handlePlayPause}>
                {isPlaying ? <Pause size={16} /> : <Play size={16} />}
              </button>
              <button type="button" className="ve-transport-btn" onClick={handleSkipForward} title="Forward 5s">
                <SkipForward size={14} />
              </button>
            </div>

            <div className="ve-timeline-area">
              <div className="ve-timeline" onClick={handleSeek} role="slider" tabIndex={0}>
                {isTrimming && (
                  <>
                    <div className="ve-trim-excluded ve-trim-excluded-start" style={{ width: `${trimStart * 100}%` }} />
                    <div className="ve-trim-excluded ve-trim-excluded-end" style={{ width: `${(1 - trimEnd) * 100}%`, right: 0 }} />
                    <TrimHandle position={trimStart} side="start" onDrag={handleTrimStartChange} />
                    <TrimHandle position={trimEnd} side="end" onDrag={handleTrimEndChange} />
                  </>
                )}
                {trimSegments.map((seg, idx) => (
                  <div
                    key={idx}
                    className="ve-cut-segment"
                    style={{ left: `${seg.start * 100}%`, width: `${(seg.end - seg.start) * 100}%` }}
                    title="Cut segment (click to remove)"
                    onClick={(e) => { e.stopPropagation(); handleRemoveSegment(idx) }}
                  />
                ))}
                <div className="ve-timeline-fill" style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }} />
                <div className="ve-timeline-cursor" style={{ left: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }} />
              </div>

              <div className="ve-time-display">
                <span>{formatTime(currentTime)}</span>
                <span className="ve-time-sep">/</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            <div className="ve-volume">
              <button type="button" className="ve-transport-btn" onClick={handleToggleMute}>
                {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
              </button>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="ve-volume-slider"
              />
            </div>
          </div>

          {isTrimming && (
            <div className="ve-trim-controls">
              <div className="ve-trim-info">
                <span>Trim: {formatTime(trimStart * duration)} - {formatTime(trimEnd * duration)}</span>
                <span className="ve-trim-duration">
                  ({formatTime((trimEnd - trimStart) * duration)})
                </span>
              </div>
              <div className="ve-trim-actions">
                <button type="button" className="ve-btn" onClick={handleAddTrimCut} title="Add cut at playhead">
                  <Scissors size={14} /> Cut Here
                </button>
                <button
                  type="button"
                  className="ve-btn ve-btn-primary"
                  onClick={handleApplyTrim}
                  disabled={isApplyingTrim}
                  title="Send trim/cut edits to agent"
                >
                  {isApplyingTrim ? <RefreshCw size={14} /> : <Send size={14} />} Apply Trim
                </button>
                <button
                  type="button"
                  className="ve-btn"
                  onClick={() => { setTrimStart(0); setTrimEnd(1); setTrimSegments([]) }}
                  title="Reset trim"
                >
                  <RotateCw size={14} /> Reset
                </button>
              </div>
              {trimSegments.length > 0 && (
                <div className="ve-segments-list">
                  <span className="ve-segments-label">Cuts:</span>
                  {trimSegments.map((seg, idx) => (
                    <span key={idx} className="ve-segment-chip">
                      {formatTime(seg.start * duration)}-{formatTime(seg.end * duration)}
                      <button type="button" onClick={() => handleRemoveSegment(idx)} className="ve-segment-remove">
                        <Trash2 size={10} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
