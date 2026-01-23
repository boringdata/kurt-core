import { useState, useEffect, useCallback } from 'react'
import WorkflowRow from './WorkflowRow'

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

  // Initial fetch and polling
  useEffect(() => {
    fetchWorkflows(false)
    const interval = setInterval(() => fetchWorkflows(false), 5000)
    return () => clearInterval(interval)
  }, [statusFilter, typeFilter, searchQuery])

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
    setExpandedId(expandedId === workflowId ? null : workflowId)
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
