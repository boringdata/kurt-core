/**
 * Tests for WorkflowList component
 *
 * Features tested:
 * - Workflow listing and pagination
 * - Status filtering
 * - Search by ID
 * - Polling and refresh
 * - Expand/collapse workflow rows
 * - Action callbacks
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import WorkflowList from '../../components/WorkflowList'
import { workflows, createWorkflowList } from '../fixtures'
import { setupApiMocks, flushPromises } from '../utils'

describe('WorkflowList', () => {
  const defaultProps = {
    onAttachWorkflow: vi.fn(),
  }

  beforeEach(() => {
    setupApiMocks({
      '/api/workflows': { workflows: createWorkflowList(5) },
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders workflow list with items', async () => {
      render(<WorkflowList {...defaultProps} />)

      // Flush all pending timers and promises
      await new Promise(r => setTimeout(r, 10))

      expect(screen.getAllByText(/fetch|map/).length).toBeGreaterThan(0)
    })

    it('shows status filter dropdown', async () => {
      render(<WorkflowList {...defaultProps} />)

      expect(screen.getByText('All')).toBeInTheDocument()
    })

    it('shows search input', async () => {
      render(<WorkflowList {...defaultProps} />)

      expect(screen.getByPlaceholderText(/id/i)).toBeInTheDocument()
    })

    it('shows refresh button', async () => {
      render(<WorkflowList {...defaultProps} />)

      expect(screen.getByTitle(/refresh/i)).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('shows loading state initially', () => {
      render(<WorkflowList {...defaultProps} />)

      expect(screen.getByText(/loading/i)).toBeInTheDocument()
    })

    it('hides loading state after data loads', async () => {
      render(<WorkflowList {...defaultProps} />)

      // Flush all pending timers and promises
      await new Promise(r => setTimeout(r, 10))

      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('shows error message when fetch fails', async () => {
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')))

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument()
      })
    })
  })

  describe('Empty State', () => {
    it('shows message when no workflows', async () => {
      setupApiMocks({
        '/api/workflows': { workflows: [] },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        expect(screen.getByText(/no workflows/i)).toBeInTheDocument()
      })
    })
  })

  describe('Status Filtering', () => {
    it('filters by PENDING status', async () => {
      const allWorkflows = createWorkflowList(10)
      setupApiMocks({
        '/api/workflows': (url: string) => {
          // Simulate server-side filtering
          if (url.includes('status=PENDING')) {
            return { workflows: allWorkflows.filter(w => w.status === 'PENDING') }
          }
          return { workflows: allWorkflows }
        },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      fireEvent.change(screen.getByDisplayValue('All'), { target: { value: 'PENDING' } })

      await waitFor(() => {
        // After filter, should only show PENDING workflows
        expect(screen.queryByText('SUCCESS')).not.toBeInTheDocument()
        expect(screen.queryByText('ERROR')).not.toBeInTheDocument()
      })
    })

    it('shows all workflows with "All" filter', async () => {
      setupApiMocks({
        '/api/workflows': { workflows: createWorkflowList(5) },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        expect(screen.getAllByRole('button').length).toBeGreaterThan(1)
      })
    })

    it.each(['Running', 'Success', 'Failed', 'Cancelled', 'Queued'])(
      'has %s filter option',
      async (filterOption) => {
        render(<WorkflowList {...defaultProps} />)

        const select = screen.getByDisplayValue('All')
        expect(select).toContainHTML(filterOption)
      }
    )
  })

  describe('Search', () => {
    it('sends search parameter in API request', async () => {
      const fetchMock = setupApiMocks({
        '/api/workflows': { workflows: createWorkflowList(5) },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      const searchInput = screen.getByPlaceholderText(/id/i)
      fireEvent.change(searchInput, { target: { value: 'workflow-0' } })

      // Wait for the search to trigger a new fetch
      await waitFor(() => {
        const searchCalls = fetchMock.mock.calls.filter(call => call[0].includes('search='))
        expect(searchCalls.length).toBeGreaterThan(0)
      })
    })

    it('debounces search input', async () => {
      const fetchMock = setupApiMocks({
        '/api/workflows': { workflows: createWorkflowList(5) },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      const searchInput = screen.getByPlaceholderText(/id/i)

      // Type multiple characters quickly
      fireEvent.change(searchInput, { target: { value: 'a' } })
      fireEvent.change(searchInput, { target: { value: 'ab' } })
      fireEvent.change(searchInput, { target: { value: 'abc' } })

      const callsBeforeDebounce = fetchMock.mock.calls.length

      await new Promise(r => setTimeout(r, 10))

      // Should not have made many additional calls due to debouncing
      expect(fetchMock.mock.calls.length - callsBeforeDebounce).toBeLessThanOrEqual(1)
    })
  })

  describe('Refresh', () => {
    it('refreshes list when refresh button is clicked', async () => {
      const fetchMock = setupApiMocks({
        '/api/workflows': { workflows: createWorkflowList(5) },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      const callsBeforeRefresh = fetchMock.mock.calls.length

      fireEvent.click(screen.getByTitle(/refresh/i))

      await new Promise(r => setTimeout(r, 10))

      expect(fetchMock.mock.calls.length).toBeGreaterThan(callsBeforeRefresh)
    })

    it('sets up polling interval for updates', async () => {
      const setIntervalSpy = vi.spyOn(global, 'setInterval')

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      // Verify that setInterval was called for polling
      expect(setIntervalSpy).toHaveBeenCalled()

      setIntervalSpy.mockRestore()
    })
  })

  describe('Expand/Collapse', () => {
    it('expands workflow row on click', async () => {
      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        const firstRow = screen.getAllByText(/fetch|map/)[0].closest('.workflow-row-header')
        if (firstRow) {
          fireEvent.click(firstRow)
        }
      })

      await waitFor(() => {
        expect(screen.getByText('Full ID:')).toBeInTheDocument()
      })
    })

    it('collapses expanded row on second click', async () => {
      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        const firstRow = screen.getAllByText(/fetch|map/)[0].closest('.workflow-row-header')
        if (firstRow) {
          // Expand
          fireEvent.click(firstRow)
        }
      })

      await waitFor(() => {
        expect(screen.getByText('Full ID:')).toBeInTheDocument()
      })

      await waitFor(() => {
        const firstRow = screen.getAllByText(/fetch|map/)[0].closest('.workflow-row-header')
        if (firstRow) {
          // Collapse
          fireEvent.click(firstRow)
        }
      })

      await waitFor(() => {
        expect(screen.queryByText('Full ID:')).not.toBeInTheDocument()
      })
    })

    it('only expands one row at a time', async () => {
      setupApiMocks({
        '/api/workflows': { workflows: createWorkflowList(3) },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        const rows = document.querySelectorAll('.workflow-row-header')
        expect(rows.length).toBeGreaterThan(1)
      })

      // Click first row
      const firstRow = document.querySelectorAll('.workflow-row-header')[0]
      fireEvent.click(firstRow)

      await waitFor(() => {
        expect(screen.getByText('Full ID:')).toBeInTheDocument()
      })

      // Click second row
      const secondRow = document.querySelectorAll('.workflow-row-header')[1]
      fireEvent.click(secondRow)

      await waitFor(() => {
        // Should still only have one expanded
        const expandedRows = document.querySelectorAll('.workflow-row.expanded')
        expect(expandedRows.length).toBe(1)
      })
    })
  })

  describe('Action Callbacks', () => {
    it('calls onAttachWorkflow when attach button is clicked', async () => {
      setupApiMocks({
        '/api/workflows': { workflows: [workflows.pending] },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        const attachButton = screen.getByTitle('Attach terminal')
        fireEvent.click(attachButton)
      })

      expect(defaultProps.onAttachWorkflow).toHaveBeenCalled()
    })

    it('calls cancel API when cancel button is clicked', async () => {
      const fetchMock = setupApiMocks({
        '/api/workflows': { workflows: [workflows.pending] },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        const cancelButton = screen.getByTitle('Cancel workflow')
        fireEvent.click(cancelButton)
      })

      // Cancel triggers an API call, not a callback prop
      await waitFor(() => {
        const cancelCalls = fetchMock.mock.calls.filter(call => call[0].includes('/cancel'))
        expect(cancelCalls.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Status Badges', () => {
    it.each([
      ['SUCCESS', 'workflow-status-success'],
      ['ERROR', 'workflow-status-error'],
      ['PENDING', 'workflow-status-pending'],
      ['ENQUEUED', 'workflow-status-enqueued'],
      ['CANCELLED', 'workflow-status-cancelled'],
    ])('applies correct class for %s status', async (status, expectedClass) => {
      setupApiMocks({
        '/api/workflows': {
          workflows: [{ ...workflows.pending, status }],
        },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        const badge = screen.getByText(status)
        expect(badge).toHaveClass(expectedClass)
      })
    })
  })

  describe('Limit and Pagination', () => {
    it('requests workflows with limit parameter', async () => {
      const fetchMock = setupApiMocks({
        '/api/workflows': { workflows: createWorkflowList(50) },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      // Verify limit=50 was included in the API request
      const workflowCalls = fetchMock.mock.calls.filter(call => call[0].includes('/api/workflows'))
      expect(workflowCalls.some(call => call[0].includes('limit=50'))).toBe(true)
    })

    it('shows load more button when page is full', async () => {
      setupApiMocks({
        '/api/workflows': { workflows: createWorkflowList(50) },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        expect(screen.getByText(/load more/i)).toBeInTheDocument()
      })
    })

    it('hides load more button when less than page size', async () => {
      setupApiMocks({
        '/api/workflows': { workflows: createWorkflowList(10) },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        expect(screen.queryByText(/load more/i)).not.toBeInTheDocument()
      })
    })

    it('loads more workflows when load more button is clicked', async () => {
      const fetchMock = setupApiMocks({
        '/api/workflows': (url: string) => {
          // Simulate pagination
          if (url.includes('offset=50')) {
            return { workflows: createWorkflowList(10) }
          }
          return { workflows: createWorkflowList(50) }
        },
      })

      render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      await waitFor(() => {
        expect(screen.getByText(/load more/i)).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText(/load more/i))

      await new Promise(r => setTimeout(r, 10))

      // Verify offset parameter was used
      await waitFor(() => {
        const offsetCalls = fetchMock.mock.calls.filter(call => call[0].includes('offset=50'))
        expect(offsetCalls.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Cleanup', () => {
    it('cleans up polling interval on unmount', async () => {
      const clearIntervalSpy = vi.spyOn(global, 'clearInterval')

      const { unmount } = render(<WorkflowList {...defaultProps} />)

      await new Promise(r => setTimeout(r, 10))

      unmount()

      expect(clearIntervalSpy).toHaveBeenCalled()
    })
  })
})
