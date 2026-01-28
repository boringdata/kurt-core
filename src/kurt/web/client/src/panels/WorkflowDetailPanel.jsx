import { useState, useEffect, useCallback, useRef } from 'react'
import { ArrowLeft, RefreshCw, Copy, ExternalLink } from 'lucide-react'
import WorkflowTimeline from '../components/WorkflowTimeline'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

// Auto-refresh intervals
const REFRESH_INTERVAL_RUNNING = 2000
const REFRESH_INTERVAL_COMPLETED = 30000

const formatDuration = (ms) => {
  if (ms == null) return '-'
  if (ms < 1000) return `${ms}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)
  return `${minutes}m ${remainingSeconds}s`
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  try {
    // Handle numeric timestamps
    if (/^\d+$/.test(dateStr)) {
      const date = new Date(parseInt(dateStr, 10))
      if (!isNaN(date.getTime())) return date.toLocaleString()
    }
    // Try parsing as-is
    let date = new Date(dateStr)
    if (!isNaN(date.getTime())) return date.toLocaleString()
    // Handle space-separated format
    if (typeof dateStr === 'string' && dateStr.includes(' ')) {
      date = new Date(dateStr.replace(' ', 'T') + 'Z')
      if (!isNaN(date.getTime())) return date.toLocaleString()
    }
    return '-'
  } catch {
    return '-'
  }
}

const formatTokens = (tokens) => {
  if (tokens == null) return '-'
  return tokens.toLocaleString()
}

const formatCost = (cost) => {
  if (cost == null) return '-'
  if (cost < 0.01) return `$${cost.toFixed(4)}`
  return `$${cost.toFixed(2)}`
}

const getStatusBadgeClass = (status) => {
  switch (status) {
    case 'SUCCESS':
      return 'workflow-status-success'
    case 'WARNING':
      return 'workflow-status-warning'
    case 'ERROR':
    case 'RETRIES_EXCEEDED':
      return 'workflow-status-error'
    case 'PENDING':
      return 'workflow-status-pending'
    case 'ENQUEUED':
      return 'workflow-status-enqueued'
    case 'CANCELLED':
      return 'workflow-status-cancelled'
    default:
      return ''
  }
}

const formatStepName = (stepName) => {
  if (!stepName) return 'Unknown'
  return stepName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function StatusBadge({ status }) {
  return (
    <span className={`workflow-detail-status-badge ${getStatusBadgeClass(status)}`}>
      {status}
    </span>
  )
}

function MetadataSection({ workflow, liveStatus }) {
  const inputs = liveStatus?.inputs || workflow?.inputs
  const metadata = liveStatus?.metadata || {}

  const workflowType = workflow?.workflow_type || metadata?.workflow_type
  const definitionName = workflow?.definition_name || metadata?.definition_name
  const trigger = workflow?.trigger || metadata?.trigger

  return (
    <div className="workflow-detail-metadata">
      <div className="workflow-detail-meta-grid">
        <div className="workflow-detail-meta-row">
          <span className="workflow-detail-meta-label">Type</span>
          <span className="workflow-detail-meta-value">
            <span className={`workflow-type-badge ${workflowType === 'agent' ? 'workflow-type-agent' : 'workflow-type-tool'}`}>
              {workflowType || 'unknown'}
            </span>
          </span>
        </div>
        {definitionName && (
          <div className="workflow-detail-meta-row">
            <span className="workflow-detail-meta-label">Definition</span>
            <span className="workflow-detail-meta-value workflow-detail-mono">{definitionName}</span>
          </div>
        )}
        {trigger && (
          <div className="workflow-detail-meta-row">
            <span className="workflow-detail-meta-label">Trigger</span>
            <span className="workflow-detail-meta-value">{trigger}</span>
          </div>
        )}
        <div className="workflow-detail-meta-row">
          <span className="workflow-detail-meta-label">Duration</span>
          <span className="workflow-detail-meta-value workflow-detail-mono">
            {formatDuration(liveStatus?.duration_ms)}
          </span>
        </div>
        <div className="workflow-detail-meta-row">
          <span className="workflow-detail-meta-label">Created</span>
          <span className="workflow-detail-meta-value">{formatDateTime(workflow?.created_at)}</span>
        </div>
        <div className="workflow-detail-meta-row">
          <span className="workflow-detail-meta-label">Updated</span>
          <span className="workflow-detail-meta-value">{formatDateTime(workflow?.updated_at)}</span>
        </div>
      </div>
    </div>
  )
}

function InputsSection({ liveStatus }) {
  const inputs = liveStatus?.inputs
  if (!inputs) return null

  let displayInputs = inputs
  if (typeof inputs === 'string') {
    try {
      displayInputs = JSON.parse(inputs)
    } catch {
      // Show as raw string
      return (
        <div className="workflow-detail-section">
          <h3 className="workflow-detail-section-title">Inputs</h3>
          <div className="workflow-detail-inputs-raw">
            <code>{inputs}</code>
          </div>
        </div>
      )
    }
  }

  if (typeof displayInputs !== 'object' || displayInputs === null) {
    return null
  }

  // Filter out internal fields
  const filteredInputs = {}
  for (const [key, value] of Object.entries(displayInputs)) {
    if (key.startsWith('_')) continue
    if (value === null || value === undefined || value === '') continue
    if (key === 'dry_run' && value === false) continue
    filteredInputs[key] = value
  }

  if (Object.keys(filteredInputs).length === 0) return null

  const formatValue = (value) => {
    if (typeof value === 'boolean') return value ? 'true' : 'false'
    if (typeof value === 'number') return String(value)
    if (Array.isArray(value)) return value.join(', ')
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  return (
    <div className="workflow-detail-section">
      <h3 className="workflow-detail-section-title">Inputs</h3>
      <div className="workflow-detail-inputs-grid">
        {Object.entries(filteredInputs).map(([key, value]) => (
          <div key={key} className="workflow-detail-input-row">
            <span className="workflow-detail-input-key">{key}</span>
            <span className="workflow-detail-input-value" title={formatValue(value)}>
              {formatValue(value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function StepsSection({ liveStatus }) {
  const steps = liveStatus?.steps || []

  if (steps.length === 0) return null

  return (
    <div className="workflow-detail-section">
      <h3 className="workflow-detail-section-title">Steps ({steps.length})</h3>
      <div className="workflow-detail-steps">
        {steps.map((step, idx) => {
          const hasErrors = (step.errors?.length > 0) || (step.error > 0)
          const statusColor = hasErrors || step.status === 'error'
            ? 'error'
            : step.status === 'success' || step.status === 'completed'
              ? 'success'
              : step.status === 'running' || step.status === 'in_progress'
                ? 'running'
                : 'pending'

          return (
            <div key={step.name || idx} className="workflow-detail-step-card">
              <div className="workflow-detail-step-header">
                <span className={`workflow-detail-step-status workflow-detail-step-status-${statusColor}`} />
                <span className="workflow-detail-step-name">{formatStepName(step.name)}</span>
                <span className="workflow-detail-step-duration">
                  {formatDuration(step.duration_ms)}
                </span>
              </div>
              <div className="workflow-detail-step-stats">
                <span className="workflow-detail-step-stat workflow-detail-step-success">
                  {step.success ?? step.output_count ?? 0} ok
                </span>
                <span className="workflow-detail-step-stat workflow-detail-step-error">
                  {step.error ?? step.errors?.length ?? 0} errors
                </span>
              </div>
              {step.errors && step.errors.length > 0 && (
                <div className="workflow-detail-step-errors">
                  {step.errors.slice(0, 5).map((err, errIdx) => (
                    <div key={errIdx} className="workflow-detail-step-error-msg">
                      {err.length > 200 ? `${err.slice(0, 200)}...` : err}
                    </div>
                  ))}
                  {step.errors.length > 5 && (
                    <div className="workflow-detail-step-error-more">
                      +{step.errors.length - 5} more errors
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function OutputSection({ workflow, liveStatus }) {
  const output = liveStatus?.output || {}
  const workflowError = liveStatus?.error || workflow?.error
  const workflowStatus = liveStatus?.status || workflow?.status

  const isCompleted = ['SUCCESS', 'ERROR', 'CANCELLED', 'completed', 'failed', 'canceled', 'completed_with_errors'].includes(workflowStatus)

  const hasAgentOutput = output.agent_turns != null || output.tokens_in != null || output.tool_calls != null
  const hasToolOutput = output.total_output != null || output.total_success != null
  const hasErrors = output.total_errors > 0 || workflowError

  if (!isCompleted && !hasErrors) return null
  if (!hasAgentOutput && !hasToolOutput && !hasErrors && !output.result_preview) return null

  return (
    <div className="workflow-detail-section">
      <h3 className="workflow-detail-section-title">Output</h3>
      <div className="workflow-detail-output">
        {workflowError && (
          <div className="workflow-detail-error-block">
            <div className="workflow-detail-error-label">Error</div>
            <div className="workflow-detail-error-message">{workflowError}</div>
          </div>
        )}

        {hasAgentOutput && (
          <div className="workflow-detail-output-grid">
            {output.agent_turns != null && (
              <div className="workflow-detail-output-item">
                <span className="workflow-detail-output-label">Turns</span>
                <span className="workflow-detail-output-value">{output.agent_turns}</span>
              </div>
            )}
            {output.tool_calls != null && (
              <div className="workflow-detail-output-item">
                <span className="workflow-detail-output-label">Tool Calls</span>
                <span className="workflow-detail-output-value">{output.tool_calls}</span>
              </div>
            )}
            {output.tokens_in != null && (
              <div className="workflow-detail-output-item">
                <span className="workflow-detail-output-label">Tokens In</span>
                <span className="workflow-detail-output-value workflow-detail-mono">
                  {formatTokens(output.tokens_in)}
                </span>
              </div>
            )}
            {output.tokens_out != null && (
              <div className="workflow-detail-output-item">
                <span className="workflow-detail-output-label">Tokens Out</span>
                <span className="workflow-detail-output-value workflow-detail-mono">
                  {formatTokens(output.tokens_out)}
                </span>
              </div>
            )}
            {output.cost_usd != null && (
              <div className="workflow-detail-output-item">
                <span className="workflow-detail-output-label">Cost</span>
                <span className="workflow-detail-output-value workflow-detail-cost">
                  {formatCost(output.cost_usd)}
                </span>
              </div>
            )}
            {output.stop_reason && (
              <div className="workflow-detail-output-item">
                <span className="workflow-detail-output-label">Stop Reason</span>
                <span className={`workflow-detail-output-value ${output.stop_reason.startsWith('error') ? 'workflow-detail-error-text' : ''}`}>
                  {output.stop_reason}
                </span>
              </div>
            )}
          </div>
        )}

        {hasToolOutput && !hasAgentOutput && (
          <div className="workflow-detail-output-grid">
            {output.total_output != null && (
              <div className="workflow-detail-output-item">
                <span className="workflow-detail-output-label">Total Output</span>
                <span className="workflow-detail-output-value">{output.total_output}</span>
              </div>
            )}
            {output.total_success != null && (
              <div className="workflow-detail-output-item">
                <span className="workflow-detail-output-label">Successful</span>
                <span className="workflow-detail-output-value workflow-detail-success-text">
                  {output.total_success}
                </span>
              </div>
            )}
            {output.total_errors != null && output.total_errors > 0 && (
              <div className="workflow-detail-output-item">
                <span className="workflow-detail-output-label">Errors</span>
                <span className="workflow-detail-output-value workflow-detail-error-text">
                  {output.total_errors}
                </span>
              </div>
            )}
          </div>
        )}

        {output.result_preview && (
          <div className="workflow-detail-result-preview">
            <div className="workflow-detail-result-label">Result Preview</div>
            <div className="workflow-detail-result-content">{output.result_preview}</div>
          </div>
        )}
      </div>
    </div>
  )
}

function ErrorSection({ liveStatus }) {
  const errors = []

  // Collect errors from status
  if (liveStatus?.error) {
    errors.push({ source: 'Workflow', message: liveStatus.error })
  }

  // Collect errors from steps
  const steps = liveStatus?.steps || []
  steps.forEach((step) => {
    if (step.errors && step.errors.length > 0) {
      step.errors.forEach((err) => {
        errors.push({ source: formatStepName(step.name), message: err })
      })
    }
  })

  if (errors.length === 0) return null

  return (
    <div className="workflow-detail-section workflow-detail-section-error">
      <h3 className="workflow-detail-section-title">Errors ({errors.length})</h3>
      <div className="workflow-detail-errors-list">
        {errors.slice(0, 20).map((err, idx) => (
          <div key={idx} className="workflow-detail-error-item">
            <span className="workflow-detail-error-source">{err.source}</span>
            <span className="workflow-detail-error-msg">{err.message}</span>
          </div>
        ))}
        {errors.length > 20 && (
          <div className="workflow-detail-errors-more">
            +{errors.length - 20} more errors
          </div>
        )}
      </div>
    </div>
  )
}

export default function WorkflowDetailPanel({ params }) {
  const { workflowId, onClose, onAttach, onCancel, onRetry } = params || {}

  const [workflow, setWorkflow] = useState(null)
  const [liveStatus, setLiveStatus] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const refreshIntervalRef = useRef(null)

  const isRunning = workflow?.status === 'PENDING' || workflow?.status === 'ENQUEUED'

  const fetchWorkflow = useCallback(async () => {
    if (!workflowId) return

    try {
      const response = await fetch(apiUrl(`/api/workflows/${workflowId}/status`))
      if (!response.ok) {
        throw new Error(`Failed to fetch workflow: ${response.status}`)
      }
      const data = await response.json()
      setLiveStatus(data)

      // Also fetch basic workflow info if not present
      if (!workflow) {
        const wfResponse = await fetch(apiUrl(`/api/workflows?search=${workflowId}&limit=1`))
        if (wfResponse.ok) {
          const wfData = await wfResponse.json()
          if (wfData.workflows && wfData.workflows.length > 0) {
            setWorkflow(wfData.workflows[0])
          }
        }
      }

      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [workflowId, workflow])

  // Initial fetch
  useEffect(() => {
    fetchWorkflow()
  }, [workflowId])

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current)
        refreshIntervalRef.current = null
      }
      return
    }

    const interval = isRunning ? REFRESH_INTERVAL_RUNNING : REFRESH_INTERVAL_COMPLETED
    refreshIntervalRef.current = setInterval(fetchWorkflow, interval)

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current)
      }
    }
  }, [autoRefresh, isRunning, fetchWorkflow])

  // SSE for real-time updates when running
  useEffect(() => {
    if (!isRunning || !workflowId) return

    const eventSource = new EventSource(
      apiUrl(`/api/workflows/${workflowId}/status/stream`)
    )

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setLiveStatus(data)
      } catch (err) {
        console.error('Failed to parse SSE data:', err)
      }
    }

    eventSource.onerror = () => {
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [isRunning, workflowId])

  const handleCopyId = () => {
    if (workflowId) {
      navigator.clipboard.writeText(workflowId).catch(() => {})
    }
  }

  const handleRefresh = () => {
    setIsLoading(true)
    fetchWorkflow()
  }

  // Compute effective status
  const getEffectiveStatus = () => {
    if (!workflow) return 'UNKNOWN'
    if (workflow.status !== 'SUCCESS') return workflow.status
    if (liveStatus?.status === 'completed_with_errors') return 'WARNING'
    const steps = liveStatus?.steps || []
    const hasErrors = steps.some((s) => s.error > 0)
    if (hasErrors) return 'WARNING'
    return workflow.status
  }

  const effectiveStatus = getEffectiveStatus()
  const workflowName = workflow?.definition_name || workflow?.name || 'Loading...'
  const shortId = workflowId?.slice(0, 8) || ''

  if (!workflowId) {
    return (
      <div className="panel-content workflow-detail-panel">
        <div className="workflow-detail-empty">No workflow ID provided</div>
      </div>
    )
  }

  return (
    <div className="panel-content workflow-detail-panel">
      {/* Header */}
      <div className="workflow-detail-header">
        <div className="workflow-detail-header-left">
          {onClose && (
            <button
              type="button"
              className="workflow-detail-back-btn"
              onClick={onClose}
              title="Back to list"
            >
              <ArrowLeft size={16} />
            </button>
          )}
          <div className="workflow-detail-title-group">
            <h2 className="workflow-detail-title">{workflowName}</h2>
            <div className="workflow-detail-id-row">
              <code className="workflow-detail-id" title={workflowId}>
                {shortId}
              </code>
              <button
                type="button"
                className="workflow-detail-copy-btn"
                onClick={handleCopyId}
                title="Copy full ID"
              >
                <Copy size={12} />
              </button>
            </div>
          </div>
        </div>
        <div className="workflow-detail-header-right">
          <StatusBadge status={effectiveStatus} />
          <span className="workflow-detail-duration">
            {formatDuration(liveStatus?.duration_ms)}
          </span>
          <div className="workflow-detail-controls">
            <label className="workflow-detail-auto-refresh">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              Auto
            </label>
            <button
              type="button"
              className="workflow-detail-refresh-btn"
              onClick={handleRefresh}
              disabled={isLoading}
              title="Refresh"
            >
              <RefreshCw size={14} className={isLoading ? 'spinning' : ''} />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="workflow-detail-content">
        {error && (
          <div className="workflow-detail-error-banner">
            {error}
          </div>
        )}

        {isLoading && !liveStatus ? (
          <div className="workflow-detail-loading">Loading workflow details...</div>
        ) : (
          <>
            {/* Progress for running workflows */}
            {isRunning && liveStatus?.stage && (
              <div className="workflow-detail-progress">
                <div className="workflow-detail-progress-header">
                  <span className="workflow-detail-stage-name">
                    {liveStatus.stage}
                  </span>
                  <span className="workflow-detail-progress-count">
                    {liveStatus.progress?.current || 0}/{liveStatus.progress?.total || '?'}
                  </span>
                </div>
                <div className="workflow-detail-progress-bar">
                  <div
                    className="workflow-detail-progress-fill"
                    style={{
                      width: `${liveStatus.progress?.total > 0
                        ? Math.round((liveStatus.progress.current / liveStatus.progress.total) * 100)
                        : 0}%`
                    }}
                  />
                </div>
              </div>
            )}

            <MetadataSection workflow={workflow} liveStatus={liveStatus} />
            <InputsSection liveStatus={liveStatus} />

            {/* Timeline visualization */}
            {liveStatus?.steps?.length > 0 && (
              <div className="workflow-detail-section">
                <h3 className="workflow-detail-section-title">Timeline</h3>
                <WorkflowTimeline steps={liveStatus.steps} />
              </div>
            )}

            <StepsSection liveStatus={liveStatus} />
            <OutputSection workflow={workflow} liveStatus={liveStatus} />
            <ErrorSection liveStatus={liveStatus} />

            {/* Action buttons for running workflows */}
            {isRunning && (
              <div className="workflow-detail-actions">
                {onAttach && (
                  <button
                    type="button"
                    className="workflow-detail-action-btn workflow-detail-attach-btn"
                    onClick={() => onAttach(workflowId)}
                  >
                    Attach Terminal
                  </button>
                )}
                {onCancel && (
                  <button
                    type="button"
                    className="workflow-detail-action-btn workflow-detail-cancel-btn"
                    onClick={() => onCancel(workflowId)}
                  >
                    Cancel
                  </button>
                )}
              </div>
            )}

            {/* Retry button for completed workflows */}
            {!isRunning && onRetry && ['SUCCESS', 'ERROR', 'CANCELLED', 'WARNING', 'RETRIES_EXCEEDED'].includes(workflow?.status) && (
              <div className="workflow-detail-actions">
                <button
                  type="button"
                  className="workflow-detail-action-btn workflow-detail-retry-btn"
                  onClick={() => onRetry(workflowId)}
                >
                  Retry Workflow
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
