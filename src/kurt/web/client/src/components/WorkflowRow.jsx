import { useState, useEffect, useCallback } from 'react'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

export default function WorkflowRow({
  workflow,
  isExpanded,
  onToggleExpand,
  onAttach,
  onCancel,
  getStatusBadgeClass,
}) {
  const [logs, setLogs] = useState('')
  const [logsLoading, setLogsLoading] = useState(false)
  const [logsError, setLogsError] = useState(null)
  const [liveStatus, setLiveStatus] = useState(null)

  const isRunning = workflow.status === 'PENDING' || workflow.status === 'ENQUEUED'

  const fetchStatus = useCallback(async () => {
    if (!workflow?.workflow_uuid) return
    try {
      const response = await fetch(
        apiUrl(`/api/workflows/${workflow.workflow_uuid}/status`)
      )
      if (response.ok) {
        const data = await response.json()
        setLiveStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch status:', err)
    }
  }, [workflow?.workflow_uuid])

  // SSE for real-time status updates
  useEffect(() => {
    if (!isExpanded || !isRunning || !workflow?.workflow_uuid) return

    const eventSource = new EventSource(
      apiUrl(`/api/workflows/${workflow.workflow_uuid}/status/stream`)
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
  }, [isExpanded, isRunning, workflow?.workflow_uuid])

  // SSE for real-time log streaming
  useEffect(() => {
    if (!isExpanded || !isRunning || !workflow?.workflow_uuid) return

    const eventSource = new EventSource(
      apiUrl(`/api/workflows/${workflow.workflow_uuid}/logs/stream`)
    )

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.content) {
          setLogs((prev) => prev + data.content)
        }
        if (data.done) {
          eventSource.close()
        }
      } catch (err) {
        console.error('Failed to parse SSE log data:', err)
      }
    }

    eventSource.onerror = () => {
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [isExpanded, isRunning, workflow?.workflow_uuid])

  const fetchLogs = useCallback(async () => {
    if (!workflow?.workflow_uuid) return
    setLogsLoading(true)
    setLogsError(null)
    try {
      const response = await fetch(
        apiUrl(`/api/workflows/${workflow.workflow_uuid}/logs?limit=300`)
      )
      if (!response.ok) {
        throw new Error(`Failed to fetch logs: ${response.status}`)
      }
      const data = await response.json()
      setLogs(data.content || '')
      if (!data.content && data.total_lines === 0) {
        setLogs('')
      }
    } catch (err) {
      setLogsError(err.message)
    } finally {
      setLogsLoading(false)
    }
  }, [workflow?.workflow_uuid])

  // Fetch initial logs and status when expanded (SSE handles live updates)
  useEffect(() => {
    if (!isExpanded) return

    fetchLogs()
    fetchStatus()
  }, [isExpanded, workflow?.workflow_uuid, fetchLogs, fetchStatus])

  const shortId = workflow.workflow_uuid?.slice(0, 8) || ''
  const workflowName = workflow.name || 'Unknown'

  const formatStageName = (stage) => {
    const stageNames = {
      discovering: 'Discovering URLs',
      fetching: 'Fetching Content',
      saving: 'Saving Files',
      embedding: 'Generating Embeddings',
      persisting: 'Saving to Database',
    }
    return stageNames[stage] || stage
  }

  const progress = liveStatus?.progress || {}
  const progressPct =
    progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0

  const formatTime = (dateStr) => {
    if (!dateStr) return '-'
    try {
      return new Date(dateStr).toLocaleTimeString()
    } catch {
      return '-'
    }
  }

  const formatDateTime = (dateStr) => {
    if (!dateStr) return '-'
    try {
      return new Date(dateStr).toLocaleString()
    } catch {
      return '-'
    }
  }

  const handleCopyId = (e) => {
    e.stopPropagation()
    if (workflow.workflow_uuid) {
      navigator.clipboard.writeText(workflow.workflow_uuid).catch(() => {})
    }
  }

  return (
    <div className={`workflow-row ${isExpanded ? 'expanded' : ''}`}>
      <div
        className="workflow-row-header"
        onClick={onToggleExpand}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onToggleExpand()
          }
        }}
      >
        <span className="workflow-expand-icon">{isExpanded ? '▼' : '▶'}</span>
        <span
          className={`workflow-status-badge ${getStatusBadgeClass(workflow.status)}`}
        >
          {workflow.status}
        </span>
        <span className="workflow-name" title={workflowName}>
          {workflowName.length > 20 ? `${workflowName.slice(0, 20)}...` : workflowName}
        </span>
        <span className="workflow-id" title={workflow.workflow_uuid}>
          {shortId}
        </span>
        <span className="workflow-time">{formatTime(workflow.created_at)}</span>
        <div className="workflow-actions" onClick={(e) => e.stopPropagation()}>
          {isRunning && (
            <>
              <button
                type="button"
                className="workflow-action-btn workflow-attach"
                onClick={onAttach}
                title="Attach terminal"
              >
                ⌨
              </button>
              <button
                type="button"
                className="workflow-action-btn workflow-cancel"
                onClick={onCancel}
                title="Cancel workflow"
              >
                ✕
              </button>
            </>
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="workflow-row-details">
          {/* Progress bar for running workflows */}
          {isRunning && liveStatus?.stage && (
            <div className="workflow-progress">
              <div className="workflow-progress-header">
                <span className="workflow-stage-name">
                  {formatStageName(liveStatus.stage)}
                </span>
                <span className="workflow-progress-count">
                  {progress.current || 0}/{progress.total || '?'}
                </span>
              </div>
              <div className="workflow-progress-bar">
                <div
                  className="workflow-progress-fill"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          )}

          {/* Results for completed workflows */}
          {workflow.status === 'SUCCESS' && liveStatus?.steps?.length > 0 && (
            <div className="workflow-results">
              {liveStatus.steps.map((step) => (
                <span key={step.name} className="workflow-result-step">
                  <span className="result-step-name">{step.name}</span>
                  <span className="result-success">{step.success || 0}</span>
                  {step.error > 0 && (
                    <span className="result-failed">{step.error}</span>
                  )}
                </span>
              ))}
            </div>
          )}

          <div className="workflow-detail-row">
            <span className="workflow-detail-label">Full ID:</span>
            <code
              className="workflow-detail-value workflow-id-copyable"
              onClick={handleCopyId}
              title="Click to copy"
            >
              {workflow.workflow_uuid}
            </code>
          </div>
          <div className="workflow-detail-row">
            <span className="workflow-detail-label">Updated:</span>
            <span className="workflow-detail-value">
              {formatDateTime(workflow.updated_at)}
            </span>
          </div>
          <div className="workflow-logs">
            <div className="workflow-logs-header">
              <span>Logs</span>
              {isRunning && <span className="workflow-logs-live">LIVE</span>}
            </div>
            <pre className="workflow-logs-content">
              {logsLoading && !logs
                ? 'Loading logs...'
                : logsError
                  ? `Error: ${logsError}`
                  : logs || 'No logs available. Use Attach for live progress.'}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
