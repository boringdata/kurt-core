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
  const [stepsExpanded, setStepsExpanded] = useState(false)
  const [inputExpanded, setInputExpanded] = useState(false)
  const [stepLogs, setStepLogs] = useState({}) // { stepName: logs[] }

  const isRunning = workflow.status === 'PENDING' || workflow.status === 'ENQUEUED'

  // Compute effective status - show WARNING if there are errors even if workflow "succeeded"
  const getEffectiveStatus = () => {
    if (workflow.status !== 'SUCCESS') return workflow.status
    // Check if liveStatus has errors
    if (liveStatus?.status === 'completed_with_errors') return 'WARNING'
    const steps = liveStatus?.steps || []
    const hasErrors = steps.some((s) => s.error > 0)
    if (hasErrors) return 'WARNING'
    return workflow.status
  }
  const effectiveStatus = getEffectiveStatus()

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

  // Fetch step logs when steps section is expanded
  const fetchStepLogs = useCallback(async (stepName) => {
    if (!workflow?.workflow_uuid || stepLogs[stepName]) return
    try {
      const response = await fetch(
        apiUrl(`/api/workflows/${workflow.workflow_uuid}/step-logs?step=${encodeURIComponent(stepName)}`)
      )
      if (response.ok) {
        const data = await response.json()
        setStepLogs((prev) => ({ ...prev, [stepName]: data.logs || [] }))
      }
    } catch (err) {
      console.error('Failed to fetch step logs:', err)
    }
  }, [workflow?.workflow_uuid, stepLogs])

  // Fetch logs for all steps when steps section is expanded
  useEffect(() => {
    if (!stepsExpanded || !liveStatus?.steps) return
    liveStatus.steps.forEach((step) => {
      fetchStepLogs(step.name)
    })
  }, [stepsExpanded, liveStatus?.steps, fetchStepLogs])

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

  const formatStepName = (stepName) => {
    const stepNames = {
      map_url: 'URL Discovery',
      map_sources: 'Source Mapping',
      fetch_documents: 'Fetch Documents',
      save_content: 'Save Content',
      generate_embeddings: 'Generate Embeddings',
      persist_documents: 'Persist to DB',
    }
    return stepNames[stepName] || stepName.replace(/_/g, ' ')
  }

  const formatDuration = (ms) => {
    if (ms == null) return null
    if (ms < 1000) return `${ms}ms`
    const seconds = ms / 1000
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.round(seconds % 60)
    return `${minutes}m ${remainingSeconds}s`
  }

  // Format inputs as a directly reusable CLI command
  const formatInputsAsCommand = (inputs, workflowType) => {
    if (!inputs) return null

    // Determine command from workflow type
    if (workflowType === 'map_workflow' || workflowType === 'map') {
      let cmd = 'kurt content map'
      if (inputs.source_url) {
        cmd += ` "${inputs.source_url}"`
      } else if (inputs.url) {
        cmd += ` "${inputs.url}"`
      }
      if (inputs.max_depth != null) cmd += ` --max-depth ${inputs.max_depth}`
      if (inputs.max_pages != null) cmd += ` --max-pages ${inputs.max_pages}`
      if (inputs.include_pattern) cmd += ` --include "${inputs.include_pattern}"`
      if (inputs.exclude_pattern) cmd += ` --exclude "${inputs.exclude_pattern}"`
      if (inputs.dry_run) cmd += ' --dry-run'
      return cmd
    } else if (workflowType === 'fetch_workflow' || workflowType === 'fetch') {
      let cmd = 'kurt content fetch'
      // fetch_engine from config maps to --engine CLI flag
      if (inputs.fetch_engine && inputs.fetch_engine !== 'trafilatura') {
        cmd += ` --engine ${inputs.fetch_engine}`
      }
      if (inputs.dry_run) cmd += ' --dry-run'
      return cmd
    }

    // Unknown workflow type - just show JSON
    return null
  }

  const progress = liveStatus?.progress || {}
  const progressPct =
    progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0

  const parseDate = (dateStr) => {
    if (!dateStr) return null
    try {
      // Check if it's a numeric timestamp (milliseconds)
      if (/^\d+$/.test(dateStr)) {
        const ts = parseInt(dateStr, 10)
        const date = new Date(ts)
        if (!isNaN(date.getTime())) return date
      }

      // Try parsing as-is first
      let date = new Date(dateStr)
      if (!isNaN(date.getTime())) return date

      // DBOS timestamps may be in format "2024-01-09 14:30:44.123456"
      // Convert to ISO format by replacing space with T
      if (typeof dateStr === 'string' && dateStr.includes(' ')) {
        date = new Date(dateStr.replace(' ', 'T') + 'Z')
        if (!isNaN(date.getTime())) return date
      }

      return null
    } catch {
      return null
    }
  }

  const formatTime = (dateStr) => {
    const date = parseDate(dateStr)
    if (!date) return '-'
    // Show date + time in compact format
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) +
      ' ' + date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  }

  const formatDateTime = (dateStr) => {
    const date = parseDate(dateStr)
    return date ? date.toLocaleString() : '-'
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
          className={`workflow-status-badge ${getStatusBadgeClass(effectiveStatus)}`}
        >
          {effectiveStatus}
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

          {/* Collapsible Input section */}
          {liveStatus?.inputs && (
            <div className="workflow-collapsible-section">
              <div
                className="workflow-section-header"
                onClick={() => setInputExpanded(!inputExpanded)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    setInputExpanded(!inputExpanded)
                  }
                }}
              >
                <span className="workflow-section-toggle">
                  {inputExpanded ? '▼' : '▶'}
                </span>
                <span className="workflow-section-label">Input</span>
                <span className="workflow-section-preview">
                  {liveStatus.inputs.source_url || liveStatus.inputs.url || '...'}
                </span>
              </div>
              {inputExpanded && (
                <div className="workflow-section-content">
                  <div className="workflow-command-wrapper">
                    <code className="workflow-inputs-content workflow-command">
                      {liveStatus.cli_command ||
                        formatInputsAsCommand(liveStatus.inputs, workflow.name) ||
                        JSON.stringify(liveStatus.inputs, null, 2)}
                    </code>
                    <button
                      type="button"
                      className="workflow-command-copy"
                      onClick={() => {
                        const cmd = liveStatus.cli_command ||
                          formatInputsAsCommand(liveStatus.inputs, workflow.name) ||
                          JSON.stringify(liveStatus.inputs)
                        navigator.clipboard.writeText(cmd).catch(() => {})
                      }}
                      title="Copy command"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                      </svg>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Collapsible Steps section */}
          {workflow.status === 'SUCCESS' && liveStatus && (
            <div className="workflow-collapsible-section">
              {(() => {
                const steps = liveStatus.steps || []
                const totalSuccess = steps.reduce((sum, s) => sum + (s.success || 0), 0)
                const totalError = steps.reduce((sum, s) => sum + (s.error || 0), 0)
                const total = totalSuccess + totalError

                if (steps.length === 0) return null

                return (
                  <>
                    <div
                      className="workflow-section-header"
                      onClick={() => setStepsExpanded(!stepsExpanded)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          setStepsExpanded(!stepsExpanded)
                        }
                      }}
                    >
                      <span className="workflow-section-toggle">
                        {stepsExpanded ? '▼' : '▶'}
                      </span>
                      <span className="workflow-section-label">Steps</span>
                      <span className="workflow-section-preview">
                        {total > 0 ? (
                          <>
                            {totalSuccess} processed
                            {totalError > 0 && `, ${totalError} failed`}
                          </>
                        ) : (
                          `${steps.length} steps`
                        )}
                      </span>
                    </div>
                    {stepsExpanded && (
                      <div className="workflow-section-content">
                        {steps.map((step, idx) => {
                          const logs = stepLogs[step.name] || []
                          const stepErrors = step.errors || []
                          return (
                            <div key={idx} className="workflow-step-item">
                              <div className="workflow-step-row">
                                <span className="workflow-step-name">
                                  {formatStepName(step.name)}
                                </span>
                                <span className="workflow-step-results">
                                  {step.total > 0 ? (
                                    <>
                                      {step.success > 0 && (
                                        <span className="step-success">{step.success} ok</span>
                                      )}
                                      {step.error > 0 && (
                                        <span className="step-error">{step.error} failed</span>
                                      )}
                                    </>
                                  ) : (
                                    <span className="step-done">done</span>
                                  )}
                                  {step.duration_ms != null && (
                                    <span className="step-duration">
                                      {formatDuration(step.duration_ms)}
                                    </span>
                                  )}
                                </span>
                              </div>
                              {/* Show error messages from step data */}
                              {stepErrors.length > 0 && (
                                <div className="workflow-step-errors">
                                  {stepErrors.map((err, errIdx) => (
                                    <div key={errIdx} className="workflow-step-error">
                                      {err}
                                    </div>
                                  ))}
                                </div>
                              )}
                              {logs.length > 0 && (
                                <div className="workflow-step-logs">
                                  {logs.map((log, logIdx) => (
                                    <div
                                      key={logIdx}
                                      className={`workflow-step-log ${log.level === 'error' ? 'log-error' : ''}`}
                                    >
                                      {log.message}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </>
                )
              })()}
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
          {liveStatus?.duration_ms != null && (
            <div className="workflow-detail-row">
              <span className="workflow-detail-label">Duration:</span>
              <span className="workflow-detail-value workflow-duration">
                {formatDuration(liveStatus.duration_ms)}
              </span>
            </div>
          )}
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
