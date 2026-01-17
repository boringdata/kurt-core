import React, { useState, useEffect, useRef, useCallback } from 'react'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

// Format time as MM:SS or HH:MM:SS
const formatTime = (seconds) => {
  if (!seconds || isNaN(seconds)) return '00:00'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) {
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

// Parse time string to seconds
const parseTime = (timeStr) => {
  const parts = timeStr.split(':').map(Number)
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
  } else if (parts.length === 2) {
    return parts[0] * 60 + parts[1]
  }
  return Number(timeStr) || 0
}

export default function VideoEditor({
  videoSrc,
  onSave,
  onGenerate,
  filePath,
}) {
  const videoRef = useRef(null)
  const timelineRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [playbackRate, setPlaybackRate] = useState(1)
  const [trimStart, setTrimStart] = useState(0)
  const [trimEnd, setTrimEnd] = useState(0)
  const [isProcessing, setIsProcessing] = useState(false)
  const [showGenerateDialog, setShowGenerateDialog] = useState(false)
  const [generatePrompt, setGeneratePrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState(null)

  // Initialize video metadata
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleLoadedMetadata = () => {
      setDuration(video.duration)
      setTrimEnd(video.duration)
    }

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime)
    }

    const handleEnded = () => {
      setIsPlaying(false)
    }

    const handleError = () => {
      setError('Failed to load video')
    }

    video.addEventListener('loadedmetadata', handleLoadedMetadata)
    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('ended', handleEnded)
    video.addEventListener('error', handleError)

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('ended', handleEnded)
      video.removeEventListener('error', handleError)
    }
  }, [videoSrc])

  // Reset trim when video changes
  useEffect(() => {
    if (duration > 0) {
      setTrimStart(0)
      setTrimEnd(duration)
    }
  }, [duration])

  // Play/Pause
  const togglePlay = useCallback(() => {
    const video = videoRef.current
    if (!video) return

    if (isPlaying) {
      video.pause()
    } else {
      video.play()
    }
    setIsPlaying(!isPlaying)
  }, [isPlaying])

  // Seek
  const handleSeek = useCallback((e) => {
    const video = videoRef.current
    const timeline = timelineRef.current
    if (!video || !timeline) return

    const rect = timeline.getBoundingClientRect()
    const pos = (e.clientX - rect.left) / rect.width
    const time = pos * duration
    video.currentTime = Math.max(0, Math.min(duration, time))
  }, [duration])

  // Skip forward/backward
  const skip = useCallback((seconds) => {
    const video = videoRef.current
    if (!video) return
    video.currentTime = Math.max(0, Math.min(duration, video.currentTime + seconds))
  }, [duration])

  // Set trim markers
  const setTrimMarker = useCallback((type) => {
    if (type === 'start') {
      setTrimStart(Math.min(currentTime, trimEnd - 1))
    } else {
      setTrimEnd(Math.max(currentTime, trimStart + 1))
    }
  }, [currentTime, trimStart, trimEnd])

  // Apply trim operation
  const handleTrim = async () => {
    if (!filePath) {
      alert('Cannot trim: no file path')
      return
    }

    setIsProcessing(true)
    setError(null)

    try {
      const response = await fetch(apiUrl('/api/media/edit'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input_path: filePath,
          operation: 'trim',
          start: formatTime(trimStart),
          end: formatTime(trimEnd),
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to trim video')
      }

      const data = await response.json()
      alert(`Video trimmed! Saved to: ${data.output_path}`)
      if (onSave) {
        onSave(data.output_path)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsProcessing(false)
    }
  }

  // Extract thumbnail
  const handleExtractThumbnail = async () => {
    if (!filePath) {
      alert('Cannot extract thumbnail: no file path')
      return
    }

    setIsProcessing(true)
    setError(null)

    try {
      const response = await fetch(apiUrl('/api/media/edit'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input_path: filePath,
          operation: 'thumbnail',
          start: formatTime(currentTime),
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to extract thumbnail')
      }

      const data = await response.json()
      alert(`Thumbnail extracted! Saved to: ${data.output_path}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsProcessing(false)
    }
  }

  // Generate video with AI
  const handleGenerate = async () => {
    if (!generatePrompt.trim()) return

    setIsGenerating(true)
    try {
      const response = await fetch(apiUrl('/api/media/generate/video'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: generatePrompt,
          duration: 5,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to generate video')
      }

      const data = await response.json()
      if (data.url && onGenerate) {
        onGenerate(data.url)
      }
      setShowGenerateDialog(false)
      setGeneratePrompt('')
    } catch (err) {
      alert(`Generation failed: ${err.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return

      switch (e.key) {
        case ' ':
          e.preventDefault()
          togglePlay()
          break
        case 'ArrowLeft':
          skip(-5)
          break
        case 'ArrowRight':
          skip(5)
          break
        case 'm':
          setIsMuted(!isMuted)
          break
        case 'i':
          setTrimMarker('start')
          break
        case 'o':
          setTrimMarker('end')
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [togglePlay, skip, isMuted, setTrimMarker])

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0
  const trimStartPercent = duration > 0 ? (trimStart / duration) * 100 : 0
  const trimEndPercent = duration > 0 ? (trimEnd / duration) * 100 : 100

  return (
    <div className="video-editor">
      {/* Video Player */}
      <div className="video-player-container">
        {error && <div className="video-error">{error}</div>}
        <video
          ref={videoRef}
          src={videoSrc}
          className="video-player"
          muted={isMuted}
          playsInline
          onClick={togglePlay}
        />
        {!videoSrc && (
          <div className="video-placeholder">
            <svg viewBox="0 0 24 24" width="64" height="64" fill="currentColor" opacity="0.3">
              <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z" />
            </svg>
            <p>No video loaded</p>
          </div>
        )}
      </div>

      {/* Controls */}
      {videoSrc && (
        <>
          {/* Timeline */}
          <div className="video-timeline-container">
            <div
              className="video-timeline"
              ref={timelineRef}
              onClick={handleSeek}
            >
              {/* Trim region highlight */}
              <div
                className="timeline-trim-region"
                style={{
                  left: `${trimStartPercent}%`,
                  width: `${trimEndPercent - trimStartPercent}%`,
                }}
              />
              {/* Progress bar */}
              <div
                className="timeline-progress"
                style={{ width: `${progress}%` }}
              />
              {/* Trim markers */}
              <div
                className="timeline-marker trim-start"
                style={{ left: `${trimStartPercent}%` }}
              />
              <div
                className="timeline-marker trim-end"
                style={{ left: `${trimEndPercent}%` }}
              />
              {/* Current position marker */}
              <div
                className="timeline-marker current"
                style={{ left: `${progress}%` }}
              />
            </div>
            <div className="timeline-times">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          {/* Playback Controls */}
          <div className="video-controls">
            <div className="controls-group">
              <button type="button" className="control-btn" onClick={() => skip(-10)} title="Back 10s">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                  <path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z" />
                </svg>
              </button>
              <button type="button" className="control-btn play-btn" onClick={togglePlay}>
                {isPlaying ? (
                  <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </button>
              <button type="button" className="control-btn" onClick={() => skip(10)} title="Forward 10s">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                  <path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z" />
                </svg>
              </button>
            </div>

            <div className="controls-group">
              <button
                type="button"
                className="control-btn"
                onClick={() => setIsMuted(!isMuted)}
                title={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted ? (
                  <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                    <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                    <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
                  </svg>
                )}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={isMuted ? 0 : volume}
                onChange={(e) => {
                  setVolume(Number(e.target.value))
                  setIsMuted(false)
                  if (videoRef.current) {
                    videoRef.current.volume = Number(e.target.value)
                  }
                }}
                className="volume-slider"
              />
            </div>

            <div className="controls-group">
              <select
                value={playbackRate}
                onChange={(e) => {
                  const rate = Number(e.target.value)
                  setPlaybackRate(rate)
                  if (videoRef.current) {
                    videoRef.current.playbackRate = rate
                  }
                }}
                className="speed-select"
              >
                <option value="0.25">0.25x</option>
                <option value="0.5">0.5x</option>
                <option value="1">1x</option>
                <option value="1.5">1.5x</option>
                <option value="2">2x</option>
              </select>
            </div>
          </div>

          {/* Edit Tools */}
          <div className="video-edit-tools">
            <div className="trim-controls">
              <span className="trim-label">Trim:</span>
              <button
                type="button"
                className="tool-btn"
                onClick={() => setTrimMarker('start')}
                title="Set trim start (I)"
              >
                [ In
              </button>
              <span className="trim-time">{formatTime(trimStart)}</span>
              <span className="trim-separator">-</span>
              <span className="trim-time">{formatTime(trimEnd)}</span>
              <button
                type="button"
                className="tool-btn"
                onClick={() => setTrimMarker('end')}
                title="Set trim end (O)"
              >
                Out ]
              </button>
              <button
                type="button"
                className="action-btn"
                onClick={handleTrim}
                disabled={isProcessing || trimStart >= trimEnd}
              >
                {isProcessing ? 'Processing...' : 'Apply Trim'}
              </button>
            </div>

            <div className="edit-actions">
              <button
                type="button"
                className="action-btn"
                onClick={handleExtractThumbnail}
                disabled={isProcessing}
              >
                Extract Frame
              </button>
              <button
                type="button"
                className="action-btn"
                onClick={() => setShowGenerateDialog(true)}
              >
                AI Generate
              </button>
            </div>
          </div>
        </>
      )}

      {/* Generate Dialog */}
      {showGenerateDialog && (
        <div className="generate-dialog-overlay" onClick={() => setShowGenerateDialog(false)}>
          <div className="generate-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Generate Video with AI</h3>
            <textarea
              value={generatePrompt}
              onChange={(e) => setGeneratePrompt(e.target.value)}
              placeholder="Describe the video you want to generate..."
              rows={4}
              autoFocus
            />
            <div className="dialog-actions">
              <button
                type="button"
                className="action-btn"
                onClick={() => setShowGenerateDialog(false)}
                disabled={isGenerating}
              >
                Cancel
              </button>
              <button
                type="button"
                className="action-btn primary"
                onClick={handleGenerate}
                disabled={isGenerating || !generatePrompt.trim()}
              >
                {isGenerating ? 'Generating...' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
