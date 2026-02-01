import { useState, useEffect, useCallback, useMemo } from 'react'
import { Copy, ChevronDown, ChevronRight } from 'lucide-react'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

const MAX_WORKFLOW_DEPTH = 3

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

const normalizeInputsArgs = (inputs) => {
  if (!inputs) return null
  if (Array.isArray(inputs)) return inputs
  if (Array.isArray(inputs.args)) return inputs.args
  return null
}

const isUrlValue = (value) => {
  if (typeof value !== 'string') return false
  return value.startsWith('http://') || value.startsWith('https://')
}

const getChildInputRows = (inputs) => {
  const args = normalizeInputsArgs(inputs)
  if (!args || args.length === 0) return []

  const firstArg = args[0]
  const docIds = Array.isArray(args[4]) ? args[4] : null
  const singleDocId = typeof args[4] === 'string' ? args[4] : null

  if (typeof firstArg === 'string' && isUrlValue(firstArg)) {
    return [{ docId: singleDocId, url: firstArg }]
  }

  if (Array.isArray(firstArg)) {
    const urls = firstArg.filter((value) => isUrlValue(value))
    return urls.map((url, idx) => ({
      docId: docIds && docIds[idx] ? docIds[idx] : null,
      url,
    }))
  }

  return []
}

const formatDocId = (docId) => {
  if (!docId) return '-'
  if (docId.length <= 12) return docId
  return `${docId.slice(0, 8)}…`
}

const formatInputsAsCommand = (inputs, workflowType) => {
  if (!inputs) return null

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
  }
  if (workflowType === 'fetch_workflow' || workflowType === 'fetch') {
    let cmd = 'kurt content fetch'
    if (inputs.fetch_engine && inputs.fetch_engine !== 'trafilatura') {
      cmd += ` --engine ${inputs.fetch_engine}`
    }
    if (inputs.dry_run) cmd += ' --dry-run'
    return cmd
  }

  return null
}

const resolveWorkflowCommand = (liveStatus, workflow) => {
  if (liveStatus?.cli_command) return liveStatus.cli_command
  if (workflow?.cli_command) return workflow.cli_command
  if (liveStatus?.inputs) {
    if (typeof liveStatus.inputs === 'string') return liveStatus.inputs
    const formatted = formatInputsAsCommand(
      liveStatus.inputs,
      workflow?.name || workflow?.workflow_type
    )
    if (formatted) return formatted
    try {
      return JSON.stringify(liveStatus.inputs, null, 2)
    } catch {
      return String(liveStatus.inputs)
    }
  }
  return null
}

function CommandBlock({ command }) {
  if (!command) return null
  return (
    <div className="workflow-command-section">
      <div className="workflow-command-label">Input</div>
      <div className="workflow-command-wrapper">
        <code className="workflow-inputs-content workflow-command">
          {command}
        </code>
        <button
          type="button"
          className="workflow-command-copy"
          onClick={() => {
            navigator.clipboard.writeText(command).catch(() => {})
          }}
          title="Copy command"
        >
          <Copy size={14} />
        </button>
      </div>
    </div>
  )
}

function StepBox({
  step,
  logs,
  events,
  isExpanded,
  onToggle,
  onOpen,
  children,
  showLogs = true,
  maxDuration = 1,
  isLoadingEvents = false,
}) {
  const successCount = step.success ?? 0
  const errorCount = step.error ?? 0
  const duration = formatDuration(step.duration_ms) || '-'
  const resolvedStatus = errorCount > 0
    ? 'error'
    : step.status === 'error'
      ? 'error'
      : step.status === 'success' || step.status === 'completed'
        ? 'success'
        : successCount > 0
          ? 'success'
          : 'running'
  const statusClass = resolvedStatus === 'error'
    ? 'step-status-error'
    : resolvedStatus === 'success' || resolvedStatus === 'completed'
      ? 'step-status-success'
      : 'step-status-running'

  // Timeline bar width calculation
  const durationMs = step.duration_ms || 0
  const barWidthPercent = maxDuration > 0 ? Math.max((durationMs / maxDuration) * 100, 2) : 2

  const handleToggle = () => {
    if (!isExpanded && onOpen && showLogs) {
      onOpen()
    }
    onToggle()
  }

  const formatEventTime = (timestamp) => {
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
    <div className="workflow-step-box">
      <div
        className="workflow-step-box-header"
        onClick={handleToggle}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            handleToggle()
          }
        }}
      >
        <span className="workflow-step-box-toggle">{isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}</span>
        <span className={`workflow-step-status ${statusClass}`} />
        <span className="workflow-step-box-title">{formatStepName(step.name)}</span>
        <span className="workflow-step-box-meta">
          <span className="step-meta-success">{successCount} ok</span>
          <span className="step-meta-error">
            {errorCount} error{errorCount === 1 ? '' : 's'}
          </span>
          <span className="step-meta-duration">{duration}</span>
        </span>
      </div>
      {isExpanded && (
        <div className="workflow-step-box-body">
          {/* Timeline bar */}
          <div className="workflow-step-timeline-bar-container">
            <div
              className={`workflow-step-timeline-bar workflow-step-timeline-bar-${resolvedStatus}`}
              style={{ width: `${barWidthPercent}%` }}
              title={`Duration: ${duration}`}
            />
            <span className="workflow-step-timeline-duration">{duration}</span>
          </div>

          {/* Step errors */}
          {step.errors?.length > 0 && (
            <div className="workflow-step-errors">
              {step.errors.map((err, errIdx) => (
                <div key={errIdx} className="workflow-step-error">
                  {err}
                </div>
              ))}
            </div>
          )}

          {/* Step details from logs metadata */}
          {showLogs && logs?.length > 0 && logs[0]?.metadata && (
            <div className="workflow-step-details">
              <div className="workflow-step-details-header">Details</div>
              <div className="workflow-step-details-grid">
                {logs[0].tool && (
                  <div className="workflow-step-details-row">
                    <span className="workflow-step-details-label">Tool</span>
                    <span className="workflow-step-details-value">{logs[0].tool}</span>
                  </div>
                )}
                {logs[0].metadata.model && (
                  <div className="workflow-step-details-row">
                    <span className="workflow-step-details-label">Model</span>
                    <span className="workflow-step-details-value">{logs[0].metadata.model}</span>
                  </div>
                )}
                {logs[0].metadata.tokens_in != null && (
                  <div className="workflow-step-details-row">
                    <span className="workflow-step-details-label">Tokens In</span>
                    <span className="workflow-step-details-value">{logs[0].metadata.tokens_in?.toLocaleString()}</span>
                  </div>
                )}
                {logs[0].metadata.tokens_out != null && (
                  <div className="workflow-step-details-row">
                    <span className="workflow-step-details-label">Tokens Out</span>
                    <span className="workflow-step-details-value">{logs[0].metadata.tokens_out?.toLocaleString()}</span>
                  </div>
                )}
                {logs[0].metadata.cost_usd != null && (
                  <div className="workflow-step-details-row">
                    <span className="workflow-step-details-label">Cost</span>
                    <span className="workflow-step-details-value workflow-step-details-cost">
                      ${logs[0].metadata.cost_usd < 0.01 ? logs[0].metadata.cost_usd.toFixed(4) : logs[0].metadata.cost_usd.toFixed(2)}
                    </span>
                  </div>
                )}
                {logs[0].metadata.stop_reason && (
                  <div className="workflow-step-details-row">
                    <span className="workflow-step-details-label">Stop Reason</span>
                    <span className="workflow-step-details-value">{logs[0].metadata.stop_reason}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step events (from logs endpoint) */}
          {showLogs && (
            <div className="workflow-step-events">
              <div className="workflow-step-events-header">
                <span className="workflow-step-events-title">Events</span>
                {events && <span className="workflow-step-events-count">{events.length}</span>}
              </div>
              {isLoadingEvents ? (
                <div className="workflow-step-events-loading">Loading...</div>
              ) : events && events.length > 0 ? (
                <div className="workflow-step-events-list">
                  {events.map((event, idx) => {
                    const isToolCall = event.substep === 'tool_call'
                    const toolMeta = event.metadata || {}
                    return (
                      <div key={event.id || idx} className={`workflow-step-event workflow-step-event-${event.status || 'info'} ${isToolCall ? 'workflow-step-event-tool' : ''}`}>
                        <span className="workflow-step-event-icon">{isToolCall ? '⚙' : getEventIcon(event.status)}</span>
                        <span className="workflow-step-event-time">{formatEventTime(event.created_at)}</span>
                        <span className="workflow-step-event-message">{event.message || event.status}</span>
                        {event.current != null && event.total != null && (
                          <span className="workflow-step-event-progress">{event.current}/{event.total}</span>
                        )}
                        {isToolCall && toolMeta.input_summary && (
                          <div className="workflow-step-event-tool-detail">
                            <span className="workflow-step-event-tool-label">Input:</span>
                            <code className="workflow-step-event-tool-code">{toolMeta.input_summary}</code>
                          </div>
                        )}
                        {isToolCall && toolMeta.result_summary && (
                          <div className="workflow-step-event-tool-detail">
                            <span className="workflow-step-event-tool-label">Output:</span>
                            <code className="workflow-step-event-tool-code">{toolMeta.result_summary.length > 200 ? `${toolMeta.result_summary.slice(0, 200)}...` : toolMeta.result_summary}</code>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="workflow-step-events-empty">No events recorded</div>
              )}
            </div>
          )}
          {children}
        </div>
      )}
    </div>
  )
}

function WorkflowStepsSection({
  workflow,
  liveStatus,
  getStatusBadgeClass,
  onAttach,
  onCancel,
  depth = 0,
}) {
  const [stepsExpanded, setStepsExpanded] = useState(false)
  const [expandedSteps, setExpandedSteps] = useState({})
  const [stepLogs, setStepLogs] = useState({})
  const [stepEvents, setStepEvents] = useState({})
  const [loadingEvents, setLoadingEvents] = useState({})
  const [childWorkflows, setChildWorkflows] = useState([])
  const [childFetchAttempted, setChildFetchAttempted] = useState(false)

  useEffect(() => {
    setStepsExpanded(depth > 0)
    setExpandedSteps({})
    setStepLogs({})
    setStepEvents({})
    setLoadingEvents({})
    setChildWorkflows([])
    setChildFetchAttempted(false)
  }, [workflow?.workflow_uuid])

  const steps = liveStatus?.steps || []
  const totalSuccess = steps.reduce((sum, s) => sum + (s.success || 0), 0)
  const totalError = steps.reduce((sum, s) => sum + (s.error || 0), 0)
  const total = totalSuccess + totalError

  // Calculate max duration for timeline bar scaling
  const maxDuration = useMemo(() => {
    return Math.max(...steps.map((s) => s.duration_ms || 0), 1)
  }, [steps])

  const hasSteps = steps.length > 0 ||
    childWorkflows.length > 0 ||
    workflow?.workflow_type === 'agent'

  // Fetch step events from logs endpoint
  const fetchStepEvents = useCallback(async (stepName) => {
    if (!workflow?.workflow_uuid || stepEvents[stepName] || loadingEvents[stepName]) return
    setLoadingEvents((prev) => ({ ...prev, [stepName]: true }))
    try {
      const response = await fetch(
        apiUrl(`/api/workflows/${workflow.workflow_uuid}/logs?step_id=${encodeURIComponent(stepName)}&limit=50`)
      )
      if (response.ok) {
        const data = await response.json()
        setStepEvents((prev) => ({ ...prev, [stepName]: data.events || [] }))
      }
    } catch (err) {
      console.error('Failed to fetch step events:', err)
      setStepEvents((prev) => ({ ...prev, [stepName]: [] }))
    } finally {
      setLoadingEvents((prev) => ({ ...prev, [stepName]: false }))
    }
  }, [workflow?.workflow_uuid, stepEvents, loadingEvents])

  const fetchStepLogs = useCallback(async (stepName) => {
    if (!workflow?.workflow_uuid || stepLogs[stepName]) return
    // Also fetch events when fetching logs
    fetchStepEvents(stepName)
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
  }, [workflow, stepLogs])

  const fetchChildWorkflows = useCallback(async () => {
    if (!workflow?.workflow_uuid || childFetchAttempted) return
    setChildFetchAttempted(true)
    try {
      const response = await fetch(
        apiUrl(`/api/workflows?parent_id=${workflow.workflow_uuid}&limit=50`)
      )
      if (response.ok) {
        const data = await response.json()
        setChildWorkflows(data.workflows || [])
      }
    } catch (err) {
      console.error('Failed to fetch child workflows:', err)
    }
  }, [workflow, childFetchAttempted])

  useEffect(() => {
    if (stepsExpanded) {
      fetchChildWorkflows()
    }
  }, [stepsExpanded, fetchChildWorkflows])

  useEffect(() => {
    if (depth === 0 || !stepsExpanded) return
    if (steps.length !== 1) return
    const stepName = steps[0]?.name
    if (!stepName || expandedSteps[stepName]) return
    setExpandedSteps((prev) => ({ ...prev, [stepName]: true }))
    fetchStepLogs(stepName)
  }, [depth, stepsExpanded, steps, expandedSteps, fetchStepLogs])

  useEffect(() => {
    const stepHasErrors = steps.some(
      (step) => (step.error || 0) > 0 || (step.errors && step.errors.length > 0)
    )
    const hasErrorStatus = workflow?.status === 'ERROR' ||
      liveStatus?.status === 'error' ||
      liveStatus?.status === 'completed_with_errors' ||
      stepHasErrors

    if (!hasErrorStatus) return
    if (!stepsExpanded) {
      setStepsExpanded(true)
    }

    const stepsWithErrors = steps.filter((step) =>
      (step.error || 0) > 0 || (step.errors && step.errors.length > 0) || step.status === 'error'
    )
    if (stepsWithErrors.length === 0) return
    setExpandedSteps((prev) => {
      const next = { ...prev }
      stepsWithErrors.forEach((step) => {
        next[step.name] = true
      })
      return next
    })
    stepsWithErrors.forEach((step) => {
      fetchStepLogs(step.name)
    })
  }, [workflow?.status, liveStatus?.status, steps, stepsExpanded, fetchStepLogs])

  if (!hasSteps) return null

  const queueSteps = steps.filter((step) => step.step_type === 'queue')
  const fallbackQueueStep = queueSteps.length === 1 ? queueSteps[0].name : null
  const fallbackFetchStep = steps.find((step) => step.name === 'fetch_documents')?.name
  const assignedChildren = new Set()
  const stepChildren = steps.reduce((acc, step) => {
    acc[step.name] = []
    return acc
  }, {})

  childWorkflows.forEach((child) => {
    const parentStepName = child.parent_step_name
    if (parentStepName && stepChildren[parentStepName]) {
      stepChildren[parentStepName].push(child)
      assignedChildren.add(child.workflow_uuid)
      return
    }
    if (!parentStepName && fallbackFetchStep) {
      const childName = child.name || ''
      if (childName.includes('fetch_single_url') || childName.includes('fetch_url_batch')) {
        stepChildren[fallbackFetchStep].push(child)
        assignedChildren.add(child.workflow_uuid)
        return
      }
    }
    if (!parentStepName && fallbackQueueStep && child.name?.startsWith('<temp>')) {
      stepChildren[fallbackQueueStep].push(child)
      assignedChildren.add(child.workflow_uuid)
    }
  })

  const unassignedChildren = childWorkflows.filter(
    (child) => !assignedChildren.has(child.workflow_uuid)
  )

  const stepCount = steps.length + unassignedChildren.length
  const summaryText = total > 0
    ? `${totalSuccess} processed${totalError > 0 ? `, ${totalError} failed` : ''}` +
        (childWorkflows.length > 0
          ? ` + ${childWorkflows.length} workflow${childWorkflows.length !== 1 ? 's' : ''}`
          : '')
    : `${stepCount} step${stepCount !== 1 ? 's' : ''}` +
        (childWorkflows.length > 0
          ? ` + ${childWorkflows.length} workflow${childWorkflows.length !== 1 ? 's' : ''}`
          : '')

  return (
    <div className="workflow-collapsible-section">
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
          {stepsExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
        <span className="workflow-section-label">Steps</span>
        <span className="workflow-section-preview">{summaryText}</span>
      </div>
      {stepsExpanded && (
        <div className="workflow-section-content">
          {steps.map((step) => {
            const stepIsExpanded = !!expandedSteps[step.name]
            const stepChildrenList = stepChildren[step.name] || []
            const showStepLogs = stepChildrenList.length === 0

            return (
              <StepBox
                key={step.name}
                step={step}
                logs={stepLogs[step.name]}
                events={stepEvents[step.name]}
                isExpanded={stepIsExpanded}
                showLogs={showStepLogs}
                maxDuration={maxDuration}
                isLoadingEvents={loadingEvents[step.name]}
                onToggle={() =>
                  setExpandedSteps((prev) => ({
                    ...prev,
                    [step.name]: !prev[step.name],
                  }))
                }
                onOpen={() => fetchStepLogs(step.name)}
              >
                {stepChildrenList.length > 0 && depth < MAX_WORKFLOW_DEPTH && (
                  <div className="workflow-step-children">
                    {stepChildrenList.map((child) => (
                      <WorkflowChildBox
                        key={child.workflow_uuid}
                        workflow={child}
                        getStatusBadgeClass={getStatusBadgeClass}
                        onAttach={onAttach}
                        onCancel={onCancel}
                        depth={depth + 1}
                      />
                    ))}
                  </div>
                )}
              </StepBox>
            )
          })}
          {unassignedChildren.length > 0 && depth < MAX_WORKFLOW_DEPTH && (
            <div className="workflow-unassigned-children">
              {unassignedChildren.map((child) => (
                <WorkflowChildBox
                  key={child.workflow_uuid}
                  workflow={child}
                  getStatusBadgeClass={getStatusBadgeClass}
                  onAttach={onAttach}
                  onCancel={onCancel}
                  depth={depth + 1}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function WorkflowChildBox({
  workflow,
  getStatusBadgeClass,
  onAttach,
  onCancel,
  depth = 0,
}) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [autoExpanded, setAutoExpanded] = useState(false)
  const [liveStatus, setLiveStatus] = useState(null)
  const [statusError, setStatusError] = useState(null)

  useEffect(() => {
    setIsExpanded(false)
    setAutoExpanded(false)
    setLiveStatus(null)
    setStatusError(null)
  }, [workflow?.workflow_uuid])

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
      setStatusError(err)
    }
  }, [workflow])

  useEffect(() => {
    if (!liveStatus && !statusError) {
      fetchStatus()
    }
  }, [liveStatus, statusError, fetchStatus])

  useEffect(() => {
    if (autoExpanded) return
    const stepHasErrors = (liveStatus?.steps || []).some(
      (step) => (step.error || 0) > 0 || (step.errors && step.errors.length > 0) || step.status === 'error'
    )
    const hasErrorStatus = workflow?.status === 'ERROR' ||
      liveStatus?.status === 'error' ||
      liveStatus?.status === 'completed_with_errors' ||
      stepHasErrors

    if (hasErrorStatus) {
      setIsExpanded(true)
      setAutoExpanded(true)
    }
  }, [autoExpanded, liveStatus, workflow?.status])

  const workflowNameRaw = workflow.definition_name || workflow.name || 'Unknown'
  const workflowName = workflowNameRaw.startsWith('<temp>.')
    ? workflowNameRaw.replace(/^<temp>\./, '')
    : workflowNameRaw
  const shortId = workflow.workflow_uuid?.slice(0, 8) || ''
  const command = resolveWorkflowCommand(liveStatus, workflow)
  const duration = formatDuration(liveStatus?.duration_ms)
  const statusLabel = workflow.status || 'UNKNOWN'
  const childInputRows = getChildInputRows(liveStatus?.inputs)
  const docSummary = childInputRows.length === 1
    ? childInputRows[0]
    : childInputRows.length > 1
      ? { count: childInputRows.length, url: childInputRows[0]?.url }
      : null

  return (
    <div className="workflow-child-box" style={{ marginLeft: depth * 12 }}>
      <div
        className="workflow-child-header"
        onClick={() => setIsExpanded((prev) => !prev)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setIsExpanded((prev) => !prev)
          }
        }}
      >
        <span className="workflow-child-toggle">{isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}</span>
        <span className={`workflow-status-badge ${getStatusBadgeClass(statusLabel)}`}>
          {statusLabel}
        </span>
        <span className="workflow-child-name" title={workflowName}>
          {workflowName}
        </span>
        <span className="workflow-child-id" title={workflow.workflow_uuid}>
          {shortId}
        </span>
        {duration && <span className="workflow-child-duration">{duration}</span>}
      </div>
      {docSummary && (
        <div className="workflow-child-doc-summary">
          {docSummary.docId ? (
            <span className="workflow-child-doc-field">
              <span className="workflow-child-doc-label">Doc</span>
              <span
                className="workflow-child-doc-value"
                title={docSummary.docId}
              >
                {formatDocId(docSummary.docId)}
              </span>
            </span>
          ) : docSummary.count ? (
            <span className="workflow-child-doc-field">
              <span className="workflow-child-doc-label">Docs</span>
              <span className="workflow-child-doc-value">{docSummary.count}</span>
            </span>
          ) : null}
          {docSummary.url && (
            <span className="workflow-child-doc-field workflow-child-doc-url">
              <span className="workflow-child-doc-label">URL</span>
              <span
                className="workflow-child-doc-value"
                title={docSummary.url}
              >
                {docSummary.url}
              </span>
            </span>
          )}
        </div>
      )}
      {isExpanded && (
        <div className="workflow-child-body">
          {childInputRows.length > 0 && (
            <div className="workflow-child-input-meta">
              <div className="workflow-child-input-meta-label">Subprocess</div>
              <div className="workflow-child-input-meta-list">
                {childInputRows.map((row, idx) => (
                  <div key={`${row.url}-${idx}`} className="workflow-child-input-meta-row">
                    <span className="workflow-child-input-meta-id">
                      {row.docId || '-'}
                    </span>
                    <span className="workflow-child-input-meta-url">
                      {row.url}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <CommandBlock command={command} />
          {liveStatus ? (
            <WorkflowStepsSection
              workflow={workflow}
              liveStatus={liveStatus}
              getStatusBadgeClass={getStatusBadgeClass}
              onAttach={onAttach}
              onCancel={onCancel}
              depth={depth}
            />
          ) : statusError ? (
            <div className="workflow-child-error">Failed to load workflow status.</div>
          ) : (
            <div className="workflow-child-loading">Loading workflow details...</div>
          )}
        </div>
      )}
    </div>
  )
}

function WorkflowConfigSection({ workflow, liveStatus }) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Get inputs from liveStatus or workflow
  const inputs = liveStatus?.inputs || workflow?.inputs
  const metadata = liveStatus?.metadata || {}

  // Get workflow-specific metadata
  const workflowType = workflow?.workflow_type || metadata?.workflow_type
  const definitionName = workflow?.definition_name || metadata?.definition_name
  const trigger = workflow?.trigger || metadata?.trigger

  // Parse inputs if it's a string
  let parsedInputs = inputs
  if (typeof inputs === 'string') {
    try {
      parsedInputs = JSON.parse(inputs)
    } catch {
      parsedInputs = null
    }
  }

  // Filter out internal/empty fields from inputs
  const getDisplayInputs = () => {
    if (!parsedInputs || typeof parsedInputs !== 'object') return null
    if (Array.isArray(parsedInputs)) return parsedInputs

    const filtered = {}
    for (const [key, value] of Object.entries(parsedInputs)) {
      // Skip internal fields and empty values
      if (key.startsWith('_')) continue
      if (value === null || value === undefined || value === '') continue
      if (key === 'dry_run' && value === false) continue
      filtered[key] = value
    }
    return Object.keys(filtered).length > 0 ? filtered : null
  }

  const displayInputs = getDisplayInputs()

  // Don't show section if there's nothing to display
  const hasContent = definitionName || trigger || displayInputs || workflowType
  if (!hasContent) return null

  // Build preview text
  const previewParts = []
  if (definitionName) previewParts.push(definitionName)
  if (trigger) previewParts.push(`trigger: ${trigger}`)
  if (displayInputs && !definitionName) {
    const inputCount = Object.keys(displayInputs).length
    previewParts.push(`${inputCount} input${inputCount !== 1 ? 's' : ''}`)
  }
  const previewText = previewParts.join(' | ') || 'Configuration'

  const formatValue = (value) => {
    if (typeof value === 'boolean') return value ? 'true' : 'false'
    if (typeof value === 'number') return String(value)
    if (Array.isArray(value)) return value.join(', ')
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  return (
    <div className="workflow-collapsible-section workflow-config-section">
      <div
        className="workflow-section-header workflow-config-header"
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setIsExpanded(!isExpanded)
          }
        }}
      >
        <span className="workflow-section-toggle">
          {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
        <span className="workflow-section-icon">⚙</span>
        <span className="workflow-section-label">Config</span>
        <span className="workflow-section-preview">{previewText}</span>
      </div>
      {isExpanded && (
        <div className="workflow-section-content">
          <div className="workflow-config-grid">
            {workflowType && (
              <div className="workflow-config-row">
                <span className="workflow-config-label">Type</span>
                <span className="workflow-config-value">{workflowType}</span>
              </div>
            )}
            {definitionName && (
              <div className="workflow-config-row">
                <span className="workflow-config-label">Definition</span>
                <span className="workflow-config-value workflow-config-definition">
                  {definitionName}
                </span>
              </div>
            )}
            {trigger && (
              <div className="workflow-config-row">
                <span className="workflow-config-label">Trigger</span>
                <span className="workflow-config-value">{trigger}</span>
              </div>
            )}
            {displayInputs && (
              <>
                <div className="workflow-config-divider" />
                <div className="workflow-config-row workflow-config-inputs-header">
                  <span className="workflow-config-label">Inputs</span>
                </div>
                {Object.entries(displayInputs).map(([key, value]) => (
                  <div key={key} className="workflow-config-row workflow-config-input-row">
                    <span className="workflow-config-input-key">{key}</span>
                    <span className="workflow-config-input-value" title={formatValue(value)}>
                      {formatValue(value)}
                    </span>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function WorkflowOutputSection({ workflow, liveStatus }) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Get output info from liveStatus or workflow
  const output = liveStatus?.output || {}
  const workflowError = liveStatus?.error || workflow?.error
  const workflowStatus = liveStatus?.status || workflow?.status

  // Determine if workflow is completed (SUCCESS or ERROR)
  const isCompleted = ['SUCCESS', 'ERROR', 'CANCELLED', 'completed', 'failed', 'canceled', 'completed_with_errors'].includes(workflowStatus)

  // Check if there's anything to show
  const hasAgentOutput = output.agent_turns != null || output.tokens_in != null || output.tool_calls != null || output.stop_reason
  const hasToolOutput = output.total_output != null || output.total_success != null
  const hasErrors = output.total_errors > 0 || workflowError
  const hasResultPreview = !!output.result_preview

  // Don't show for running workflows or if there's nothing to display
  if (!isCompleted) return null
  if (!hasAgentOutput && !hasToolOutput && !hasErrors && !hasResultPreview) return null

  // Auto-expand if there are errors
  const shouldAutoExpand = hasErrors

  // Build preview text
  const previewParts = []
  if (workflowStatus === 'ERROR' || workflowStatus === 'failed' || workflowStatus === 'canceled') {
    previewParts.push('Error')
  } else if (output.total_errors > 0) {
    previewParts.push(`${output.total_errors} error${output.total_errors !== 1 ? 's' : ''}`)
  } else {
    previewParts.push('Completed')
  }

  if (output.agent_turns != null) {
    previewParts.push(`${output.agent_turns} turn${output.agent_turns !== 1 ? 's' : ''}`)
  }
  if (output.tool_calls != null) {
    previewParts.push(`${output.tool_calls} tool call${output.tool_calls !== 1 ? 's' : ''}`)
  }
  if (output.total_success != null && output.total_success > 0) {
    previewParts.push(`${output.total_success} processed`)
  }

  const previewText = previewParts.join(' | ')

  const formatCostValue = (cost) => {
    if (cost == null) return '-'
    if (cost < 0.01) return `$${cost.toFixed(4)}`
    return `$${cost.toFixed(2)}`
  }

  const formatTokens = (tokens) => {
    if (tokens == null) return '-'
    return tokens.toLocaleString()
  }

  return (
    <div className={`workflow-collapsible-section workflow-output-section ${hasErrors ? 'workflow-output-error' : ''}`}>
      <div
        className="workflow-section-header workflow-output-header"
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setIsExpanded(!isExpanded)
          }
        }}
      >
        <span className="workflow-section-toggle">
          {isExpanded || shouldAutoExpand ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
        <span className="workflow-section-icon">📊</span>
        <span className="workflow-section-label">Output</span>
        <span className={`workflow-section-preview ${hasErrors ? 'workflow-output-error-text' : ''}`}>
          {previewText}
        </span>
      </div>
      {(isExpanded || shouldAutoExpand) && (
        <div className="workflow-section-content">
          {/* Error message display */}
          {workflowError && (
            <div className="workflow-output-error-block">
              <div className="workflow-output-error-label">Error</div>
              <div className="workflow-output-error-message">{workflowError}</div>
            </div>
          )}

          {/* Agent workflow output */}
          {hasAgentOutput && (
            <div className="workflow-output-grid">
              {output.agent_turns != null && (
                <div className="workflow-output-row">
                  <span className="workflow-output-label">Turns</span>
                  <span className="workflow-output-value">{output.agent_turns}</span>
                </div>
              )}
              {output.tool_calls != null && (
                <div className="workflow-output-row">
                  <span className="workflow-output-label">Tool Calls</span>
                  <span className="workflow-output-value">{output.tool_calls}</span>
                </div>
              )}
              {output.tokens_in != null && (
                <div className="workflow-output-row">
                  <span className="workflow-output-label">Tokens In</span>
                  <span className="workflow-output-value">{formatTokens(output.tokens_in)}</span>
                </div>
              )}
              {output.tokens_out != null && (
                <div className="workflow-output-row">
                  <span className="workflow-output-label">Tokens Out</span>
                  <span className="workflow-output-value">{formatTokens(output.tokens_out)}</span>
                </div>
              )}
              {output.cost_usd != null && (
                <div className="workflow-output-row">
                  <span className="workflow-output-label">Cost</span>
                  <span className="workflow-output-value workflow-output-cost">{formatCostValue(output.cost_usd)}</span>
                </div>
              )}
              {output.stop_reason && (
                <div className="workflow-output-row">
                  <span className="workflow-output-label">Stop Reason</span>
                  <span className={`workflow-output-value ${output.stop_reason.startsWith('error') ? 'workflow-output-error-text' : ''}`}>
                    {output.stop_reason}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Tool workflow output */}
          {hasToolOutput && !hasAgentOutput && (
            <div className="workflow-output-grid">
              {output.total_output != null && (
                <div className="workflow-output-row">
                  <span className="workflow-output-label">Total Output</span>
                  <span className="workflow-output-value">{output.total_output}</span>
                </div>
              )}
              {output.total_success != null && (
                <div className="workflow-output-row">
                  <span className="workflow-output-label">Successful</span>
                  <span className="workflow-output-value workflow-output-success">{output.total_success}</span>
                </div>
              )}
              {output.total_errors != null && output.total_errors > 0 && (
                <div className="workflow-output-row">
                  <span className="workflow-output-label">Errors</span>
                  <span className="workflow-output-value workflow-output-error-text">{output.total_errors}</span>
                </div>
              )}
            </div>
          )}

          {/* Result preview for agent workflows */}
          {hasResultPreview && (
            <div className="workflow-output-preview">
              <div className="workflow-output-preview-label">Result Preview</div>
              <div className="workflow-output-preview-content">
                {output.result_preview}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const formatTokenCount = (tokens) => {
  if (tokens == null) return null
  if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`
  return String(tokens)
}

const formatCost = (cost) => {
  if (cost == null) return null
  if (cost < 0.01) return `$${cost.toFixed(4)}`
  return `$${cost.toFixed(2)}`
}

export default function WorkflowRow({
  workflow,
  isExpanded,
  onToggleExpand,
  onAttach,
  onCancel,
  onRetry,
  onOpenDetail,
  getStatusBadgeClass,
  depth = 0,
}) {
  const [liveStatus, setLiveStatus] = useState(null)
  const [isRetrying, setIsRetrying] = useState(false)

  const isRunning = workflow.status === 'PENDING' || workflow.status === 'ENQUEUED'
  const canRetry = ['SUCCESS', 'ERROR', 'CANCELLED', 'WARNING', 'RETRIES_EXCEEDED'].includes(workflow.status)

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

  // Summary info for collapsed state
  const tokensIn = workflow.tokens_in ? formatTokenCount(workflow.tokens_in) : null
  const tokensOut = workflow.tokens_out ? formatTokenCount(workflow.tokens_out) : null
  const costDisplay = workflow.cost_usd ? formatCost(workflow.cost_usd) : null
  const turns = workflow.agent_turns

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
  }, [workflow])

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

  // Fetch status on mount for completed workflows to determine effective status
  useEffect(() => {
    if (workflow.status === 'SUCCESS' && !liveStatus) {
      fetchStatus()
    }
  }, [workflow.status, workflow?.workflow_uuid, fetchStatus, liveStatus])

  // Fetch initial status when expanded (SSE handles live updates)
  useEffect(() => {
    if (!isExpanded) return

    fetchStatus()
  }, [isExpanded, workflow?.workflow_uuid, fetchStatus])

  const shortId = workflow.workflow_uuid?.slice(0, 8) || ''
  // Use definition_name for agent workflows, otherwise use the workflow name
  const workflowName = workflow.definition_name || workflow.name || 'Unknown'
  const command = resolveWorkflowCommand(liveStatus, workflow)

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

      // Timestamps may be in format "2024-01-09 14:30:44.123456"
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

  const handleRetry = async (e) => {
    e.stopPropagation()
    if (isRetrying || !onRetry) return
    setIsRetrying(true)
    try {
      await onRetry()
    } finally {
      setIsRetrying(false)
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
        <span className="workflow-expand-icon">{isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}</span>
        <span
          className={`workflow-type-badge ${workflow.workflow_type === 'agent' ? 'workflow-type-agent' : 'workflow-type-tool'}`}
          title={workflow.workflow_type === 'agent' ? 'Agent workflow' : 'Tool workflow'}
        >
          {workflow.workflow_type === 'agent' ? 'agent' : 'tool'}
        </span>
        <span
          className={`workflow-status-badge ${getStatusBadgeClass(effectiveStatus)}`}
        >
          {effectiveStatus}
        </span>
        <span className="workflow-name" title={workflow.definition_name || workflowName}>
          {workflowName.length > 20 ? `${workflowName.slice(0, 20)}...` : workflowName}
        </span>
        <span className="workflow-id" title={workflow.workflow_uuid}>
          {shortId}
        </span>
        <span className="workflow-time">{formatTime(workflow.created_at)}</span>
        {workflow.workflow_type === 'agent' && (tokensIn || costDisplay) && (
          <span className="workflow-summary-inline">
            {tokensIn && <span className="workflow-summary-tokens">{tokensIn}→{tokensOut || '0'}</span>}
            {costDisplay && <span className="workflow-summary-cost">{costDisplay}</span>}
            {turns != null && <span className="workflow-summary-turns">{turns}t</span>}
          </span>
        )}
        <div className="workflow-actions" onClick={(e) => e.stopPropagation()}>
          {onOpenDetail && (
            <button
              type="button"
              className="workflow-action-btn workflow-open-detail"
              onClick={onOpenDetail}
              title="Open in panel"
            >
              ↗
            </button>
          )}
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
          {canRetry && onRetry && (
            <button
              type="button"
              className="workflow-action-btn workflow-retry"
              onClick={handleRetry}
              disabled={isRetrying}
              title="Retry workflow"
            >
              {isRetrying ? '...' : '↻'}
            </button>
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

          <div className="workflow-meta">
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
            <div className="workflow-detail-row workflow-detail-inline">
              <span className="workflow-detail-label">Duration:</span>
              <span className="workflow-detail-value workflow-duration">
                {liveStatus?.duration_ms != null
                  ? formatDuration(liveStatus.duration_ms)
                  : '-'}
              </span>
              <span className="workflow-detail-separator">•</span>
              <span className="workflow-detail-label">Updated:</span>
              <span className="workflow-detail-value">
                {formatDateTime(workflow.updated_at)}
              </span>
            </div>
            {(workflow.tokens_in || workflow.tokens_out || workflow.cost_usd) && (
              <div className="workflow-detail-row workflow-detail-inline workflow-tokens">
                {(workflow.tokens_in != null || workflow.tokens_out != null) && (
                  <>
                    <span className="workflow-detail-label">Tokens:</span>
                    <span className="workflow-detail-value workflow-token-count">
                      {workflow.tokens_in?.toLocaleString() || 0} in / {workflow.tokens_out?.toLocaleString() || 0} out
                    </span>
                  </>
                )}
                {workflow.cost_usd != null && (
                  <>
                    <span className="workflow-detail-separator">•</span>
                    <span className="workflow-detail-label">Cost:</span>
                    <span className="workflow-detail-value workflow-cost">
                      ${workflow.cost_usd.toFixed(4)}
                    </span>
                  </>
                )}
              </div>
            )}
          </div>

          <CommandBlock command={command} />
          <WorkflowConfigSection workflow={workflow} liveStatus={liveStatus} />
          {liveStatus && (
            <WorkflowStepsSection
              workflow={workflow}
              liveStatus={liveStatus}
              getStatusBadgeClass={getStatusBadgeClass}
              onAttach={onAttach}
              onCancel={onCancel}
              depth={depth}
            />
          )}
          <WorkflowOutputSection workflow={workflow} liveStatus={liveStatus} />
        </div>
      )}
    </div>
  )
}
