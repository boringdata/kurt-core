import { useState, useEffect, useCallback } from 'react'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

/**
 * WorkflowTimeline - Horizontal timeline visualization for workflow steps
 *
 * Shows steps as horizontal bars with:
 * - Step name on the left
 * - Duration bar proportional to execution time
 * - Status color coding (green=success, red=error, blue=running, gray=pending)
 * - Click to expand and see step log events
 * - Hover tooltip with details (duration_ms, output_count, errors)
 */

const formatDuration = (ms) => {
  if (ms == null || ms === 0) return '-'
  if (ms < 1000) return `${ms}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)
  return `${minutes}m ${remainingSeconds}s`
}

const formatStepName = (stepName) => {
  if (!stepName) return 'Unknown'
  // Convert snake_case to Title Case
  return stepName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const getStatusColor = (step) => {
  const hasErrors = (step.errors && step.errors.length > 0) || step.error > 0
  if (hasErrors || step.status === 'error') return 'error'
  if (step.status === 'success' || step.status === 'completed') return 'success'
  if (step.status === 'running' || step.status === 'in_progress') return 'running'
  return 'pending'
}

const getStatusLabel = (status) => {
  switch (status) {
    case 'success':
      return 'Success'
    case 'error':
      return 'Error'
    case 'running':
      return 'Running'
    case 'pending':
    default:
      return 'Pending'
  }
}

function StepTooltip({ step, position }) {
  const statusColor = getStatusColor(step)
  const outputCount = step.output_count ?? step.success ?? 0
  const errorCount = step.errors?.length ?? step.error ?? 0
  const duration = formatDuration(step.duration_ms)

  return (
    <div
      className="workflow-timeline-tooltip"
      style={{
        left: position.x,
        top: position.y,
      }}
    >
      <div className="workflow-timeline-tooltip-header">
        <span className={`workflow-timeline-tooltip-status workflow-timeline-status-${statusColor}`} />
        <span className="workflow-timeline-tooltip-name">{formatStepName(step.name)}</span>
      </div>
      <div className="workflow-timeline-tooltip-content">
        <div className="workflow-timeline-tooltip-row">
          <span className="workflow-timeline-tooltip-label">Status</span>
          <span className="workflow-timeline-tooltip-value">{getStatusLabel(statusColor)}</span>
        </div>
        <div className="workflow-timeline-tooltip-row">
          <span className="workflow-timeline-tooltip-label">Duration</span>
          <span className="workflow-timeline-tooltip-value workflow-timeline-tooltip-mono">{duration}</span>
        </div>
        {outputCount > 0 && (
          <div className="workflow-timeline-tooltip-row">
            <span className="workflow-timeline-tooltip-label">Output</span>
            <span className="workflow-timeline-tooltip-value">{outputCount} items</span>
          </div>
        )}
        {errorCount > 0 && (
          <div className="workflow-timeline-tooltip-row workflow-timeline-tooltip-error">
            <span className="workflow-timeline-tooltip-label">Errors</span>
            <span className="workflow-timeline-tooltip-value">{errorCount}</span>
          </div>
        )}
        {step.errors && step.errors.length > 0 && (
          <div className="workflow-timeline-tooltip-errors">
            {step.errors.slice(0, 3).map((err, idx) => (
              <div key={idx} className="workflow-timeline-tooltip-error-msg">
                {err.length > 80 ? `${err.slice(0, 80)}...` : err}
              </div>
            ))}
            {step.errors.length > 3 && (
              <div className="workflow-timeline-tooltip-more">
                +{step.errors.length - 3} more errors
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function StepLogs({ events, isLoading }) {
  if (isLoading) {
    return (
      <div className="workflow-step-logs">
        <div className="workflow-step-logs-loading">Loading events...</div>
      </div>
    )
  }

  if (!events || events.length === 0) {
    return (
      <div className="workflow-step-logs">
        <div className="workflow-step-logs-empty">No events recorded</div>
      </div>
    )
  }

  const formatTime = (timestamp) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const getEventIcon = (status) => {
    switch (status) {
      case 'completed':
      case 'success':
        return '✓'
      case 'failed':
      case 'error':
        return '✗'
      case 'running':
      case 'progress':
        return '▸'
      default:
        return '○'
    }
  }

  return (
    <div className="workflow-step-logs">
      <div className="workflow-step-logs-header">
        <span className="workflow-step-logs-title">Step Events</span>
        <span className="workflow-step-logs-count">{events.length} events</span>
      </div>
      <div className="workflow-step-logs-list">
        {events.map((event, idx) => (
          <div key={event.id || idx} className={`workflow-step-log-entry workflow-step-log-${event.status || 'info'}`}>
            <span className="workflow-step-log-icon">{getEventIcon(event.status)}</span>
            <span className="workflow-step-log-time">{formatTime(event.created_at)}</span>
            <span className="workflow-step-log-message">{event.message || event.status}</span>
            {event.current != null && event.total != null && (
              <span className="workflow-step-log-progress">{event.current}/{event.total}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function TimelineBar({ step, maxDuration, onHover, onLeave, isExpanded, onToggle, events, isLoadingEvents }) {
  const statusColor = getStatusColor(step)
  const duration = step.duration_ms || 0
  const widthPercent = maxDuration > 0 ? Math.max((duration / maxDuration) * 100, 2) : 2

  const handleMouseEnter = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    onHover(step, {
      x: rect.left + rect.width / 2,
      y: rect.top - 8,
    })
  }

  return (
    <div className={`workflow-timeline-row ${isExpanded ? 'workflow-timeline-row-expanded' : ''}`}>
      <div
        className="workflow-timeline-label"
        title={step.name}
        onClick={onToggle}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onToggle()
          }
        }}
      >
        <span className={`workflow-timeline-expand-icon ${isExpanded ? 'expanded' : ''}`}>▶</span>
        {formatStepName(step.name)}
      </div>
      <div className="workflow-timeline-bar-container">
        <div
          className={`workflow-timeline-bar workflow-timeline-bar-${statusColor}`}
          style={{ width: `${widthPercent}%` }}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={onLeave}
          onClick={onToggle}
          role="button"
          tabIndex={0}
          aria-valuenow={duration}
          aria-valuemax={maxDuration}
          aria-label={`${formatStepName(step.name)}: ${formatDuration(duration)}`}
          aria-expanded={isExpanded}
        />
        <span className="workflow-timeline-duration">{formatDuration(duration)}</span>
      </div>
      {isExpanded && (
        <StepLogs events={events} isLoading={isLoadingEvents} />
      )}
    </div>
  )
}

export default function WorkflowTimeline({ steps = [], workflowId }) {
  const [hoveredStep, setHoveredStep] = useState(null)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })
  const [expandedSteps, setExpandedSteps] = useState(new Set())
  const [stepEvents, setStepEvents] = useState({})
  const [loadingSteps, setLoadingSteps] = useState(new Set())

  // Fetch events for a specific step
  const fetchStepEvents = useCallback(async (stepName) => {
    if (!workflowId || stepEvents[stepName] || loadingSteps.has(stepName)) return

    setLoadingSteps(prev => new Set([...prev, stepName]))
    try {
      const response = await fetch(apiUrl(`/api/workflows/${workflowId}/logs?step_id=${encodeURIComponent(stepName)}&limit=50`))
      if (response.ok) {
        const data = await response.json()
        setStepEvents(prev => ({ ...prev, [stepName]: data.events || [] }))
      }
    } catch (err) {
      console.error('Failed to fetch step events:', err)
      setStepEvents(prev => ({ ...prev, [stepName]: [] }))
    } finally {
      setLoadingSteps(prev => {
        const next = new Set(prev)
        next.delete(stepName)
        return next
      })
    }
  }, [workflowId, stepEvents, loadingSteps])

  // Handle step expansion toggle
  const handleToggleStep = useCallback((stepName) => {
    setExpandedSteps(prev => {
      const next = new Set(prev)
      if (next.has(stepName)) {
        next.delete(stepName)
      } else {
        next.add(stepName)
        // Fetch events when expanding
        fetchStepEvents(stepName)
      }
      return next
    })
  }, [fetchStepEvents])

  if (!steps || steps.length === 0) {
    return null
  }

  // Calculate max duration for scaling bars
  const maxDuration = Math.max(...steps.map((s) => s.duration_ms || 0), 1)

  const handleHover = (step, position) => {
    setHoveredStep(step)
    setTooltipPosition(position)
  }

  const handleLeave = () => {
    setHoveredStep(null)
  }

  return (
    <div className="workflow-timeline">
      <div className="workflow-timeline-header">
        <span className="workflow-timeline-title">Step Timeline</span>
        <span className="workflow-timeline-legend">
          <span className="workflow-timeline-legend-item">
            <span className="workflow-timeline-legend-dot workflow-timeline-status-success" />
            Success
          </span>
          <span className="workflow-timeline-legend-item">
            <span className="workflow-timeline-legend-dot workflow-timeline-status-error" />
            Error
          </span>
          <span className="workflow-timeline-legend-item">
            <span className="workflow-timeline-legend-dot workflow-timeline-status-running" />
            Running
          </span>
          <span className="workflow-timeline-legend-item">
            <span className="workflow-timeline-legend-dot workflow-timeline-status-pending" />
            Pending
          </span>
        </span>
      </div>
      <div className="workflow-timeline-content">
        {steps.map((step, idx) => (
          <TimelineBar
            key={step.name || idx}
            step={step}
            maxDuration={maxDuration}
            onHover={handleHover}
            onLeave={handleLeave}
            isExpanded={expandedSteps.has(step.name)}
            onToggle={() => handleToggleStep(step.name)}
            events={stepEvents[step.name]}
            isLoadingEvents={loadingSteps.has(step.name)}
          />
        ))}
      </div>
      {hoveredStep && (
        <StepTooltip step={hoveredStep} position={tooltipPosition} />
      )}
    </div>
  )
}
