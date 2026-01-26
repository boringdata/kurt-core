import { useState, useEffect, useCallback } from 'react'
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
  isExpanded,
  onToggle,
  onOpen,
  children,
  showLogs = true,
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

  const handleToggle = () => {
    if (!isExpanded && onOpen && showLogs) {
      onOpen()
    }
    onToggle()
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
          {step.errors?.length > 0 && (
            <div className="workflow-step-errors">
              {step.errors.map((err, errIdx) => (
                <div key={errIdx} className="workflow-step-error">
                  {err}
                </div>
              ))}
            </div>
          )}
          {showLogs && logs?.length > 0 && (
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
  const [childWorkflows, setChildWorkflows] = useState([])
  const [childFetchAttempted, setChildFetchAttempted] = useState(false)

  useEffect(() => {
    setStepsExpanded(depth > 0)
    setExpandedSteps({})
    setStepLogs({})
    setChildWorkflows([])
    setChildFetchAttempted(false)
  }, [workflow?.workflow_uuid])

  const steps = liveStatus?.steps || []
  const totalSuccess = steps.reduce((sum, s) => sum + (s.success || 0), 0)
  const totalError = steps.reduce((sum, s) => sum + (s.error || 0), 0)
  const total = totalSuccess + totalError

  const hasSteps = steps.length > 0 ||
    childWorkflows.length > 0 ||
    workflow?.workflow_type === 'agent'

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
                isExpanded={stepIsExpanded}
                showLogs={showStepLogs}
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
  getStatusBadgeClass,
  depth = 0,
}) {
  const [liveStatus, setLiveStatus] = useState(null)

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
        </div>
      )}
    </div>
  )
}
