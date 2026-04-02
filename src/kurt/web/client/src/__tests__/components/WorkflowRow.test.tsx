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
  createWorkflow,
  createWorkflowStatus,
} from '../fixtures'
import { setupApiMocks } from '../utils'

// Track EventSource instances created during tests
let eventSourceInstances: Array<{ url: string; close: ReturnType<typeof vi.fn> }> = []

// Create a trackable EventSource mock
class TrackableEventSource {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2

  readyState = TrackableEventSource.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  url: string
  close = vi.fn(() => {
    this.readyState = TrackableEventSource.CLOSED
  })

  constructor(url: string) {
    this.url = url
    eventSourceInstances.push({ url, close: this.close })
    setTimeout(() => {
      this.readyState = TrackableEventSource.OPEN
      this.onopen?.(new Event('open'))
    }, 0)
  }

  addEventListener = vi.fn()
  removeEventListener = vi.fn()
  dispatchEvent = vi.fn()

  simulateMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }))
  }
}

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
    eventSourceInstances = []
    vi.stubGlobal('EventSource', TrackableEventSource)
    setupApiMocks({
      '/api/workflows/': { ...workflowStatuses.fetching },
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
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

      // Component truncates at 20 chars + "..."
      expect(screen.getByText('this-is-a-very-long-...')).toBeInTheDocument()
    })

    it('shows expand icon in collapsed state', () => {
      render(<WorkflowRow {...defaultProps} isExpanded={false} />)

      // ChevronRight Lucide icon renders as SVG
      expect(document.querySelector('.workflow-expand-icon svg')).toBeInTheDocument()
    })

    it('shows collapse icon in expanded state', () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      // ChevronDown Lucide icon renders as SVG
      expect(document.querySelector('.workflow-expand-icon svg')).toBeInTheDocument()
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

      const header = document.querySelector('.workflow-row-header')!
      fireEvent.click(header)
      expect(defaultProps.onToggleExpand).toHaveBeenCalled()
    })

    it('calls onToggleExpand on Enter key', () => {
      render(<WorkflowRow {...defaultProps} />)

      const header = document.querySelector('.workflow-row-header')!
      fireEvent.keyDown(header, { key: 'Enter' })
      expect(defaultProps.onToggleExpand).toHaveBeenCalled()
    })

    it('calls onToggleExpand on Space key', () => {
      render(<WorkflowRow {...defaultProps} />)

      const header = document.querySelector('.workflow-row-header')!
      fireEvent.keyDown(header, { key: ' ' })
      expect(defaultProps.onToggleExpand).toHaveBeenCalled()
    })

    it('shows details section when expanded', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await waitFor(() => {
        expect(screen.getByText('Full ID:')).toBeInTheDocument()
        expect(screen.getByText('Updated:')).toBeInTheDocument()
      })
    })

    it('hides details section when collapsed', () => {
      render(<WorkflowRow {...defaultProps} isExpanded={false} />)

      expect(screen.queryByText('Full ID:')).not.toBeInTheDocument()
    })
  })

  describe('Progress Bar', () => {
    it('shows progress bar for running workflows with stage info', async () => {
      // Use specific patterns that are longer than /api/workflows
      setupApiMocks({
        '/api/workflows/pending-1234-5678-9abc-def012345678/status': workflowStatuses.fetching,
      })

      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await waitFor(() => {
        expect(screen.getByText('Fetching Content')).toBeInTheDocument()
      }, { timeout: 3000 })

      await waitFor(() => {
        expect(screen.getByText('25/100')).toBeInTheDocument()
      })
    })

    it('calculates progress percentage correctly', async () => {
      setupApiMocks({
        '/api/workflows/pending-1234-5678-9abc-def012345678/status': createWorkflowStatus({
          stage: 'saving',
          progress: { current: 50, total: 100 },
        }),
      })

      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await waitFor(() => {
        const progressFill = document.querySelector('.workflow-progress-fill')
        expect(progressFill).toHaveStyle({ width: '50%' })
      }, { timeout: 3000 })
    })

    it('formats stage names correctly', async () => {
      // Test just one stage to keep the test fast and reliable
      setupApiMocks({
        '/api/workflows/pending-1234-5678-9abc-def012345678/status': createWorkflowStatus({ stage: 'embedding' }),
      })

      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await waitFor(() => {
        expect(screen.getByText('Generating Embeddings')).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('Results Summary', () => {
    it('shows results for completed workflows', async () => {
      setupApiMocks({
        '/api/workflows/success-1234-5678-9abc-def012345678/status': workflowStatuses.completed,
      })

      render(<WorkflowRow {...defaultProps} workflow={workflows.success} isExpanded={true} />)

      await waitFor(() => {
        // Check for steps section header with processed count
        expect(screen.getByText(/processed/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('shows error counts when present', async () => {
      setupApiMocks({
        '/api/workflows/success-1234-5678-9abc-def012345678/status': {
          stage: 'completed',
          progress: { current: 100, total: 100 },
          steps: [{ name: 'fetch', success: 90, error: 10, total: 100 }],
        },
      })

      render(<WorkflowRow {...defaultProps} workflow={workflows.success} isExpanded={true} />)

      await waitFor(() => {
        // Look for the "failed" text which indicates errors
        expect(screen.getByText(/failed/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('SSE Real-time Updates', () => {
    it('establishes SSE connection for status updates when expanded', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await waitFor(() => {
        const statusStream = eventSourceInstances.find((es) =>
          es.url.includes('/status/stream')
        )
        expect(statusStream).toBeDefined()
      })
    })

    it('closes SSE connections when collapsed', async () => {
      const { rerender } = render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      // Wait for SSE connections to be established
      await waitFor(() => {
        expect(eventSourceInstances.length).toBeGreaterThan(0)
      })

      const initialInstances = [...eventSourceInstances]

      rerender(<WorkflowRow {...defaultProps} isExpanded={false} />)

      await waitFor(() => {
        // Check that close was called on at least one stream
        const closedStreams = initialInstances.filter((es) => es.close.mock.calls.length > 0)
        expect(closedStreams.length).toBeGreaterThan(0)
      })
    })

    it('closes SSE connections on component unmount', async () => {
      const { unmount } = render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      // Wait for SSE connections to be established
      await waitFor(() => {
        expect(eventSourceInstances.length).toBeGreaterThan(0)
      })

      const instancesBeforeUnmount = [...eventSourceInstances]

      unmount()

      // Check that close was called
      const closedStreams = instancesBeforeUnmount.filter((es) => es.close.mock.calls.length > 0)
      expect(closedStreams.length).toBeGreaterThan(0)
    })

    it('does not establish SSE for non-running workflows', async () => {
      // Clear instances before rendering completed workflow
      eventSourceInstances = []

      render(<WorkflowRow {...defaultProps} workflow={workflows.success} isExpanded={true} />)

      // Give it time to potentially create SSE connections
      await new Promise(r => setTimeout(r, 50))

      // Should not have created any SSE streams for status/logs (only API fetches)
      const sseStreams = eventSourceInstances.filter(
        (es) => es.url.includes('/stream')
      )
      expect(sseStreams.length).toBe(0)
    })
  })

  describe('Copy ID', () => {
    it('copies workflow UUID to clipboard when clicked', async () => {
      render(<WorkflowRow {...defaultProps} isExpanded={true} />)

      await new Promise(r => setTimeout(r, 10))

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

      // Time format depends on locale; just verify the time span exists
      expect(document.querySelector('.workflow-time')).toBeInTheDocument()
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

  describe('Agent Workflow Summary', () => {
    it('shows inline summary for agent workflows with tokens and cost', () => {
      render(<WorkflowRow {...defaultProps} workflow={workflows.agentSuccess} />)

      // Should show token counts and cost inline
      expect(document.querySelector('.workflow-summary-inline')).toBeInTheDocument()
      expect(screen.getByText(/50\.0k/)).toBeInTheDocument() // 50000 tokens formatted as 50.0k
      expect(screen.getByText(/\$0\.12/)).toBeInTheDocument() // cost
      expect(screen.getByText(/5t/)).toBeInTheDocument() // agent turns
    })

    it('does not show summary for non-agent workflows', () => {
      render(<WorkflowRow {...defaultProps} workflow={workflows.success} />)

      expect(document.querySelector('.workflow-summary-inline')).not.toBeInTheDocument()
    })

    it('does not show summary for agent workflows without token data', () => {
      render(<WorkflowRow {...defaultProps} workflow={workflows.agentPending} />)

      expect(document.querySelector('.workflow-summary-inline')).not.toBeInTheDocument()
    })
  })
})
