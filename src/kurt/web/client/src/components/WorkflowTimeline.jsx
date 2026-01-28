import { useState } from 'react'

/**
 * WorkflowTimeline - Horizontal timeline visualization for workflow steps
 *
 * Shows steps as horizontal bars with:
 * - Step name on the left
 * - Duration bar proportional to execution time
 * - Status color coding (green=success, red=error, blue=running, gray=pending)
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

function TimelineBar({ step, maxDuration, onHover, onLeave }) {
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
    <div className="workflow-timeline-row">
      <div className="workflow-timeline-label" title={step.name}>
        {formatStepName(step.name)}
      </div>
      <div className="workflow-timeline-bar-container">
        <div
          className={`workflow-timeline-bar workflow-timeline-bar-${statusColor}`}
          style={{ width: `${widthPercent}%` }}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={onLeave}
          role="progressbar"
          aria-valuenow={duration}
          aria-valuemax={maxDuration}
          aria-label={`${formatStepName(step.name)}: ${formatDuration(duration)}`}
        />
        <span className="workflow-timeline-duration">{formatDuration(duration)}</span>
      </div>
    </div>
  )
}

export default function WorkflowTimeline({ steps = [] }) {
  const [hoveredStep, setHoveredStep] = useState(null)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })

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
          />
        ))}
      </div>
      {hoveredStep && (
        <StepTooltip step={hoveredStep} position={tooltipPosition} />
      )}
    </div>
  )
}
