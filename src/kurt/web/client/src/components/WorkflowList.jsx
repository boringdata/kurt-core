import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import WorkflowRow from './WorkflowRow'

// Polling intervals in milliseconds
const POLLING_FAST = 2000   // When workflows are running
const POLLING_SLOW = 10000  // When all workflows are idle
const POLLING_NONE = null   // Stop polling when no workflows

// Check if a workflow has an error status that should trigger auto-expand
const hasErrorStatus = (workflow) => {
  return workflow.status === 'ERROR' ||
    workflow.status === 'RETRIES_EXCEEDED' ||
    (workflow.error_count && workflow.error_count > 0)
}

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'PENDING', label: 'Running' },
  { value: 'SUCCESS', label: 'Success' },
  { value: 'ERROR', label: 'Failed' },
  { value: 'CANCELLED', label: 'Cancelled' },
  { value: 'ENQUEUED', label: 'Queued' },
]

const TYPE_OPTIONS = [
  { value: '', label: 'All types' },
  { value: 'agent', label: 'Agent' },
  { value: 'tool', label: 'Tool' },
]

const PAGE_SIZE = 50

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

export default function WorkflowList({ onAttachWorkflow }) {
  const [workflows, setWorkflows] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [error, setError] = useState(null)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset] = useState(0)
  // Track workflows that have been auto-expanded (to avoid re-expanding after manual collapse)
  const autoExpandedRef = useRef(new Set())
  // Track if user has manually collapsed a workflow
  const userCollapsedRef = useRef(new Set())

  const fetchWorkflows = useCallback(async (loadMore = false) => {
    setIsLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (statusFilter) params.set('status', statusFilter)
      if (typeFilter) params.set('workflow_type', typeFilter)
      if (searchQuery) params.set('search', searchQuery)
      params.set('limit', String(PAGE_SIZE))
      params.set('offset', String(loadMore ? offset : 0))

      const response = await fetch(apiUrl(`/api/workflows?${params}`))
      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.status}`)
      }
      const data = await response.json()
      const newWorkflows = data.workflows || []

      if (loadMore) {
        setWorkflows(prev => [...prev, ...newWorkflows])
        setOffset(prev => prev + newWorkflows.length)
      } else {
        setWorkflows(newWorkflows)
        setOffset(newWorkflows.length)
      }

      setHasMore(newWorkflows.length === PAGE_SIZE)

      if (data.error) {
        setError(data.error)
      } else {
        setError(null)
      }
    } catch (err) {
      console.error('Failed to fetch workflows:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [statusFilter, typeFilter, searchQuery, offset])

  // Determine if any workflow is actively running
  const hasRunningWorkflows = useMemo(() => {
    return workflows.some(
      (w) => w.status === 'PENDING' || w.status === 'ENQUEUED'
    )
  }, [workflows])

  // Calculate optimal polling interval based on workflow states
  const pollingInterval = useMemo(() => {
    if (workflows.length === 0) {
      // No workflows loaded yet - poll at slow interval to check for new ones
      return POLLING_SLOW
    }
    if (hasRunningWorkflows) {
      // Active workflows - poll fast for real-time updates
      return POLLING_FAST
    }
    // All workflows completed/idle - poll slowly or stop
    // Continue slow polling to detect new workflows
    return POLLING_SLOW
  }, [workflows.length, hasRunningWorkflows])

  // Track polling interval changes for logging (debug)
  const prevIntervalRef = useRef(pollingInterval)

  // Initial fetch and adaptive polling
  useEffect(() => {
    fetchWorkflows(false)
  }, [statusFilter, typeFilter, searchQuery])

  // Adaptive polling based on workflow state
  useEffect(() => {
    if (pollingInterval === POLLING_NONE) {
      return // No polling needed
    }

    const interval = setInterval(() => {
      fetchWorkflows(false)
    }, pollingInterval)

    // Update ref for tracking
    prevIntervalRef.current = pollingInterval

    return () => clearInterval(interval)
  }, [pollingInterval, statusFilter, typeFilter, searchQuery, fetchWorkflows])

  // Auto-expand workflows with error status on first load
  useEffect(() => {
    if (workflows.length === 0) return

    // Find the first error workflow that hasn't been auto-expanded yet
    // and hasn't been manually collapsed by the user
    for (const workflow of workflows) {
      const workflowId = workflow.workflow_uuid
      if (
        hasErrorStatus(workflow) &&
        !autoExpandedRef.current.has(workflowId) &&
        !userCollapsedRef.current.has(workflowId)
      ) {
        // Mark as auto-expanded so we don't re-expand on refresh
        autoExpandedRef.current.add(workflowId)
        // Expand this workflow
        setExpandedId(workflowId)
        // Only auto-expand one workflow at a time
        break
      }
    }
  }, [workflows])

  const handleLoadMore = () => {
    fetchWorkflows(true)
  }

  const handleCancel = async (workflowId) => {
    try {
      const response = await fetch(apiUrl(`/api/workflows/${workflowId}/cancel`), {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(`Cancel failed: ${response.status}`)
      }
      // Refresh list after cancel
      fetchWorkflows(false)
    } catch (err) {
      console.error('Failed to cancel workflow:', err)
    }
  }

  const handleAttach = (workflowId) => {
    onAttachWorkflow?.(workflowId)
  }

  const handleToggleExpand = (workflowId) => {
    const isCurrentlyExpanded = expandedId === workflowId
    if (isCurrentlyExpanded) {
      // User is collapsing - track this to prevent re-auto-expand
      userCollapsedRef.current.add(workflowId)
      setExpandedId(null)
    } else {
      // User is expanding - remove from collapsed set if present
      userCollapsedRef.current.delete(workflowId)
      setExpandedId(workflowId)
    }
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

  return (
    <div className="workflow-list-container">
      <div className="workflow-list-filters">
        <select
          className="workflow-select"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label="Filter by type"
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          className="workflow-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Filter by status"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <input
          type="text"
          className="workflow-search"
          placeholder="Search by ID..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Search workflows"
        />
        <button
          type="button"
          className="workflow-refresh"
          onClick={() => fetchWorkflows(false)}
          disabled={isLoading}
          title="Refresh"
        >
          {isLoading ? '...' : '↻'}
        </button>
      </div>

      <div className="workflow-list">
        {error && (
          <div className="workflow-list-error">
            {error}
          </div>
        )}
        {workflows.length === 0 && !error ? (
          <div className="workflow-list-empty">
            {isLoading ? 'Loading...' : 'No workflows found'}
          </div>
        ) : (
          <>
            {workflows.map((workflow) => (
              <WorkflowRow
                key={workflow.workflow_uuid}
                workflow={workflow}
                isExpanded={expandedId === workflow.workflow_uuid}
                onToggleExpand={() => handleToggleExpand(workflow.workflow_uuid)}
                onAttach={() => handleAttach(workflow.workflow_uuid)}
                onCancel={() => handleCancel(workflow.workflow_uuid)}
                getStatusBadgeClass={getStatusBadgeClass}
              />
            ))}
            {hasMore && (
              <button
                type="button"
                className="workflow-load-more"
                onClick={handleLoadMore}
                disabled={isLoading}
              >
                {isLoading ? 'Loading...' : 'Load more'}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
