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

  // Fetch logs when expanded
  useEffect(() => {
    if (!isExpanded) return

    fetchLogs()

    // Auto-refresh logs for running workflows
    if (workflow.status === 'PENDING' || workflow.status === 'ENQUEUED') {
      const interval = setInterval(fetchLogs, 2000)
      return () => clearInterval(interval)
    }
  }, [isExpanded, workflow?.workflow_uuid, workflow?.status, fetchLogs])

  const isRunning = workflow.status === 'PENDING' || workflow.status === 'ENQUEUED'
  const shortId = workflow.workflow_uuid?.slice(0, 8) || ''
  const workflowName = workflow.name || 'Unknown'

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
