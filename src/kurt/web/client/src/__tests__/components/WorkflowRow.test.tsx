/**
 * Tests for WorkflowRow component
 *
 * Features tested:
 * - Workflow status display and badges
 * - Progress bar rendering
 * - SSE real-time updates
 * - Log streaming
 * - Expand/collapse behavior
 * - Action buttons (attach, cancel)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import WorkflowRow from '../../components/WorkflowRow'
import {
  workflows,
  workflowStatuses,
  workflowLogs,
  createWorkflow,
  createWorkflowStatus,
} from '../fixtures'
import { MockEventSource, setupApiMocks, flushPromises } from '../utils'

describe('WorkflowRow', () => {
  const defaultProps = {
    workflow: workflows.pending,
    isExpanded: false,
    onToggleExpand: vi.fn(),
    onAttach: vi.fn(),
    onCancel: vi.fn(),
    getStatusBadgeClass: (status: string) => `status-${status.toLowerCase()}`,
  }

  beforeEach(() => {
    vi.useFakeTimers()
    MockEventSource.clearInstances()
    setupApiMocks({
      '/api/workflows/': { ...workflowStatuses.fetching },
      '/logs': workflowLogs.short,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('Rendering', () => {
    it('renders workflow name and short ID', () => {
      render(<WorkflowRow {...defaultProps} />)

      expect(screen.getByText('fetch')).toBeInTheDocument()
      expect(screen.getByText('pending-')).toBeInTheDocument()
    })

    it('renders status badge with correct class', () => {
      render(<WorkflowRow {...defaultProps} />)

      const badge = screen.getByText('PENDING')
      expect(badge).toHaveClass('status-pending')
    })

    it('truncates long workflow names', () => {
      const longNameWorkflow = createWorkflow({
        name: 'this-is-a-very-long-workflow-name-that-should-be-truncated',
      })
      render(<WorkflowRow {...defaultProps} workflow={longNameWorkflow} />)

      expect(screen.getByText(/this-is-a-very-long-w.../)).toBeInTheDocument()
    })

    it('shows expand icon in collapsed state', () => {
      render(<WorkflowRow {...defaultProps} isExpanded={false} />)

      expect(screen.getByText('▶')).toBeInTheDocument()
    })

    it('shows collapse icon in expanded state', () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      expect(screen.getByText('▼')).toBeInTheDocument()
    })
  })

  describe('Status Badges', () => {
    it.each([
      ['PENDING', 'status-pending'],
      ['ENQUEUED', 'status-enqueued'],
      ['SUCCESS', 'status-success'],
      ['ERROR', 'status-error'],
      ['CANCELLED', 'status-cancelled'],
    ])('renders %s status with correct class', (status, expectedClass) => {
      const workflow = createWorkflow({ status: status as 'PENDING' })
      render(<WorkflowRow {...defaultProps} workflow={workflow} />)

      const badge = screen.getByText(status)
      expect(badge).toHaveClass(expectedClass)
    })
  })

  describe('Action Buttons', () => {
    it('shows attach and cancel buttons for running workflows', () => {
      render(<WorkflowRow {...defaultProps} workflow={workflows.pending} />)

      expect(screen.getByTitle('Attach terminal')).toBeInTheDocument()
      expect(screen.getByTitle('Cancel workflow')).toBeInTheDocument()
    })

    it('hides action buttons for completed workflows', () => {
      render(<WorkflowRow {...defaultProps} workflow={workflows.success} />)

      expect(screen.queryByTitle('Attach terminal')).not.toBeInTheDocument()
      expect(screen.queryByTitle('Cancel workflow')).not.toBeInTheDocument()
    })

    it('calls onAttach when attach button is clicked', async () => {
      render(<WorkflowRow {...defaultProps} />)

      fireEvent.click(screen.getByTitle('Attach terminal'))
      expect(defaultProps.onAttach).toHaveBeenCalled()
    })

    it('calls onCancel when cancel button is clicked', async () => {
      render(<WorkflowRow {...defaultProps} />)

      fireEvent.click(screen.getByTitle('Cancel workflow'))
      expect(defaultProps.onCancel).toHaveBeenCalled()
    })

    it('prevents event propagation when clicking action buttons', () => {
      render(<WorkflowRow {...defaultProps} />)

      fireEvent.click(screen.getByTitle('Attach terminal'))
      expect(defaultProps.onToggleExpand).not.toHaveBeenCalled()
    })
  })

  describe('Expand/Collapse', () => {
    it('calls onToggleExpand when header is clicked', () => {
      render(<WorkflowRow {...defaultProps} />)

      fireEvent.click(screen.getByRole('button', { name: '' }))
      expect(defaultProps.onToggleExpand).toHaveBeenCalled()
    })

    it('calls onToggleExpand on Enter key', () => {
      render(<WorkflowRow {...defaultProps} />)

      const header = screen.getByRole('button', { name: '' })
      fireEvent.keyDown(header, { key: 'Enter' })
      expect(defaultProps.onToggleExpand).toHaveBeenCalled()
    })

    it('calls onToggleExpand on Space key', () => {
      render(<WorkflowRow {...defaultProps} />)

      const header = screen.getByRole('button', { name: '' })
      fireEvent.keyDown(header, { key: ' ' })
      expect(defaultProps.onToggleExpand).toHaveBeenCalled()
    })

    it('shows details section when expanded', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await waitFor(() => {
        expect(screen.getByText('Full ID:')).toBeInTheDocument()
        expect(screen.getByText('Updated:')).toBeInTheDocument()
        expect(screen.getByText('Logs')).toBeInTheDocument()
      })
    })

    it('hides details section when collapsed', () => {
      render(<WorkflowRow {...defaultProps} isExpanded={false} />)

      expect(screen.queryByText('Full ID:')).not.toBeInTheDocument()
    })
  })

  describe('Progress Bar', () => {
    it('shows progress bar for running workflows with stage info', async () => {
      setupApiMocks({
        '/api/workflows/': workflowStatuses.fetching,
        '/logs': workflowLogs.empty,
      })

      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)
      await flushPromises()

      await waitFor(() => {
        expect(screen.getByText('Fetching Content')).toBeInTheDocument()
        expect(screen.getByText('25/100')).toBeInTheDocument()
      })
    })

    it('calculates progress percentage correctly', async () => {
      setupApiMocks({
        '/api/workflows/': createWorkflowStatus({
          stage: 'saving',
          progress: { current: 50, total: 100 },
        }),
        '/logs': workflowLogs.empty,
      })

      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        const progressFill = document.querySelector('.workflow-progress-fill')
        expect(progressFill).toHaveStyle({ width: '50%' })
      })
    })

    it('formats stage names correctly', async () => {
      const stages = [
        { stage: 'discovering', expected: 'Discovering URLs' },
        { stage: 'fetching', expected: 'Fetching Content' },
        { stage: 'saving', expected: 'Saving Files' },
        { stage: 'embedding', expected: 'Generating Embeddings' },
        { stage: 'persisting', expected: 'Saving to Database' },
      ]

      for (const { stage, expected } of stages) {
        setupApiMocks({
          '/api/workflows/': createWorkflowStatus({ stage }),
          '/logs': workflowLogs.empty,
        })

        const { unmount } = render(<WorkflowRow {...defaultProps} isExpanded={true} />)

        await vi.advanceTimersByTimeAsync(100)

        await waitFor(() => {
          expect(screen.getByText(expected)).toBeInTheDocument()
        })

        unmount()
      }
    })
  })

  describe('Results Summary', () => {
    it('shows results for completed workflows', async () => {
      setupApiMocks({
        '/api/workflows/': workflowStatuses.completed,
        '/logs': workflowLogs.empty,
      })

      render(<WorkflowRow {...defaultProps} workflow={workflows.success} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText('fetch')).toBeInTheDocument()
        expect(screen.getByText('95')).toBeInTheDocument() // success count
      })
    })

    it('shows error counts when present', async () => {
      setupApiMocks({
        '/api/workflows/': {
          stage: 'completed',
          progress: { current: 100, total: 100 },
          steps: [{ name: 'fetch', success: 90, error: 10 }],
        },
        '/logs': workflowLogs.empty,
      })

      render(<WorkflowRow {...defaultProps} workflow={workflows.success} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText('10')).toBeInTheDocument() // error count
      })
    })
  })

  describe('Logs', () => {
    it('shows loading state while fetching logs', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      expect(screen.getByText('Loading logs...')).toBeInTheDocument()
    })

    it('displays log content when loaded', async () => {
      setupApiMocks({
        '/api/workflows/': workflowStatuses.fetching,
        '/logs': workflowLogs.short,
      })

      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText(/Starting fetch workflow/)).toBeInTheDocument()
      })
    })

    it('shows LIVE indicator for running workflows', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await waitFor(() => {
        expect(screen.getByText('LIVE')).toBeInTheDocument()
      })
    })

    it('shows error message when log fetch fails', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockRejectedValue(new Error('Network error'))
      )

      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument()
      })
    })

    it('shows fallback message when no logs available', async () => {
      setupApiMocks({
        '/api/workflows/': workflowStatuses.fetching,
        '/logs': workflowLogs.empty,
      })

      render(<WorkflowRow {...defaultProps} workflow={workflows.success} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText(/No logs available/)).toBeInTheDocument()
      })
    })
  })

  describe('SSE Real-time Updates', () => {
    it('establishes SSE connection for status updates when expanded', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      const statusStream = MockEventSource.instances.find((es) =>
        es.url.includes('/status/stream')
      )
      expect(statusStream).toBeDefined()
    })

    it('establishes SSE connection for log streaming when expanded', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      const logsStream = MockEventSource.instances.find((es) =>
        es.url.includes('/logs/stream')
      )
      expect(logsStream).toBeDefined()
    })

    it('updates status when SSE message received', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      const statusStream = MockEventSource.instances.find((es) =>
        es.url.includes('/status/stream')
      )

      statusStream?.simulateMessage({
        stage: 'embedding',
        progress: { current: 75, total: 100 },
      })

      await waitFor(() => {
        expect(screen.getByText('Generating Embeddings')).toBeInTheDocument()
        expect(screen.getByText('75/100')).toBeInTheDocument()
      })
    })

    it('appends logs when SSE log message received', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      const logsStream = MockEventSource.instances.find((es) =>
        es.url.includes('/logs/stream')
      )

      logsStream?.simulateMessage({ content: '[10:30:05] New log entry\n' })

      await waitFor(() => {
        expect(screen.getByText(/New log entry/)).toBeInTheDocument()
      })
    })

    it('closes SSE connections when collapsed', async () => {
      const { rerender } = render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      const statusStream = MockEventSource.instances.find((es) =>
        es.url.includes('/status/stream')
      )

      rerender(<WorkflowRow {...defaultProps} isExpanded={false} />)

      expect(statusStream?.close).toHaveBeenCalled()
    })

    it('closes SSE connections on component unmount', async () => {
      const { unmount } = render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      const streams = MockEventSource.instances.filter(
        (es) => es.url.includes('/status/stream') || es.url.includes('/logs/stream')
      )

      unmount()

      streams.forEach((stream) => {
        expect(stream.close).toHaveBeenCalled()
      })
    })

    it('does not establish SSE for non-running workflows', async () => {
      render(<WorkflowRow {...defaultProps} workflow={workflows.success} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      const statusStream = MockEventSource.instances.find((es) =>
        es.url.includes('/status/stream')
      )
      expect(statusStream).toBeUndefined()
    })
  })

  describe('Copy ID', () => {
    it('copies workflow UUID to clipboard when clicked', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await vi.advanceTimersByTimeAsync(100)

      const fullId = screen.getByText(workflows.pending.workflow_uuid)
      fireEvent.click(fullId)

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        workflows.pending.workflow_uuid
      )
    })
  })

  describe('Time Formatting', () => {
    it('formats creation time correctly', () => {
      render(<WorkflowRow {...defaultProps} />)

      // The time should be formatted as locale time string
      expect(screen.getByText(/\d{1,2}:\d{2}:\d{2}/)).toBeInTheDocument()
    })

    it('formats update time correctly when expanded', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await waitFor(() => {
        // Should show full date-time string
        expect(screen.getByText(/\d{1,2}\/\d{1,2}\/\d{4}/)).toBeInTheDocument()
      })
    })

    it('shows dash for missing dates', () => {
      const workflowNoDate = createWorkflow({ created_at: undefined as unknown as string })
      render(<WorkflowRow {...defaultProps} workflow={workflowNoDate} />)

      expect(screen.getByText('-')).toBeInTheDocument()
    })
  })
})
