/**
 * Integration tests for SSE (Server-Sent Events) streaming
 *
 * Features tested:
 * - SSE connection establishment
 * - Real-time status updates
 * - Log streaming
 * - Connection error handling
 * - Auto-close on completion
 * - Reconnection behavior
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MockEventSource, flushPromises } from '../utils'
import { workflowStatuses, workflowLogs } from '../fixtures'

describe('SSE Streaming', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockEventSource.clearInstances()
  })

  afterEach(() => {
    vi.useRealTimers()
    MockEventSource.clearInstances()
  })

  describe('Connection Management', () => {
    it('creates EventSource with correct URL', () => {
      const url = '/api/workflows/test-123/status/stream'
      const es = new MockEventSource(url)

      expect(es.url).toBe(url)
    })

    it('starts in CONNECTING state', () => {
      const es = new MockEventSource('/api/test')

      expect(es.readyState).toBe(MockEventSource.CONNECTING)
    })

    it('transitions to OPEN state', async () => {
      const es = new MockEventSource('/api/test')

      await vi.advanceTimersByTimeAsync(10)

      expect(es.readyState).toBe(MockEventSource.OPEN)
    })

    it('calls onopen when connected', async () => {
      const es = new MockEventSource('/api/test')
      const onopen = vi.fn()
      es.onopen = onopen

      await vi.advanceTimersByTimeAsync(10)

      expect(onopen).toHaveBeenCalled()
    })

    it('tracks multiple instances', () => {
      new MockEventSource('/api/stream1')
      new MockEventSource('/api/stream2')
      new MockEventSource('/api/stream3')

      expect(MockEventSource.instances).toHaveLength(3)
    })

    it('returns last instance', () => {
      new MockEventSource('/api/stream1')
      new MockEventSource('/api/stream2')
      const last = new MockEventSource('/api/stream3')

      expect(MockEventSource.getLastInstance()).toBe(last)
    })
  })

  describe('Message Handling', () => {
    it('calls onmessage with parsed data', async () => {
      const es = new MockEventSource('/api/test')
      const onmessage = vi.fn()
      es.onmessage = onmessage

      await vi.advanceTimersByTimeAsync(10)

      es.simulateMessage({ stage: 'fetching', progress: { current: 5, total: 10 } })

      expect(onmessage).toHaveBeenCalled()
      const event = onmessage.mock.calls[0][0]
      const data = JSON.parse(event.data)
      expect(data.stage).toBe('fetching')
    })

    it('handles workflow status updates', async () => {
      const es = new MockEventSource('/api/workflows/123/status/stream')
      let receivedStatus: typeof workflowStatuses.fetching | null = null

      es.onmessage = (event) => {
        receivedStatus = JSON.parse(event.data)
      }

      await vi.advanceTimersByTimeAsync(10)

      es.simulateMessage(workflowStatuses.fetching)

      expect(receivedStatus).toEqual(workflowStatuses.fetching)
    })

    it('handles log streaming messages', async () => {
      const es = new MockEventSource('/api/workflows/123/logs/stream')
      const logs: string[] = []

      es.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.content) {
          logs.push(data.content)
        }
      }

      await vi.advanceTimersByTimeAsync(10)

      es.simulateMessage({ content: 'Log line 1\n' })
      es.simulateMessage({ content: 'Log line 2\n' })
      es.simulateMessage({ content: 'Log line 3\n' })

      expect(logs).toHaveLength(3)
      expect(logs.join('')).toContain('Log line 1')
    })

    it('does not deliver messages before OPEN state', () => {
      const es = new MockEventSource('/api/test')
      const onmessage = vi.fn()
      es.onmessage = onmessage

      // Try to send before open
      es.simulateMessage({ test: 'data' })

      expect(onmessage).not.toHaveBeenCalled()
    })
  })

  describe('Progress Updates', () => {
    it('handles stage transitions', async () => {
      const es = new MockEventSource('/api/workflows/123/status/stream')
      const stages: string[] = []

      es.onmessage = (event) => {
        const data = JSON.parse(event.data)
        stages.push(data.stage)
      }

      await vi.advanceTimersByTimeAsync(10)

      es.simulateMessage(workflowStatuses.discovering)
      es.simulateMessage(workflowStatuses.fetching)
      es.simulateMessage(workflowStatuses.saving)
      es.simulateMessage(workflowStatuses.embedding)
      es.simulateMessage(workflowStatuses.persisting)

      expect(stages).toEqual([
        'discovering',
        'fetching',
        'saving',
        'embedding',
        'persisting',
      ])
    })

    it('handles progress count updates', async () => {
      const es = new MockEventSource('/api/workflows/123/status/stream')
      const progressHistory: Array<{ current: number; total: number }> = []

      es.onmessage = (event) => {
        const data = JSON.parse(event.data)
        progressHistory.push(data.progress)
      }

      await vi.advanceTimersByTimeAsync(10)

      for (let i = 0; i <= 10; i++) {
        es.simulateMessage({
          stage: 'fetching',
          progress: { current: i * 10, total: 100 },
        })
      }

      expect(progressHistory).toHaveLength(11)
      expect(progressHistory[0].current).toBe(0)
      expect(progressHistory[10].current).toBe(100)
    })
  })

  describe('Error Handling', () => {
    it('calls onerror on error', async () => {
      const es = new MockEventSource('/api/test')
      const onerror = vi.fn()
      es.onerror = onerror

      await vi.advanceTimersByTimeAsync(10)

      es.simulateError()

      expect(onerror).toHaveBeenCalled()
    })

    it('allows closing connection on error', async () => {
      const es = new MockEventSource('/api/test')
      es.onerror = () => {
        es.close()
      }

      await vi.advanceTimersByTimeAsync(10)

      es.simulateError()

      expect(es.close).toHaveBeenCalled()
      expect(es.readyState).toBe(MockEventSource.CLOSED)
    })
  })

  describe('Connection Closing', () => {
    it('closes connection', async () => {
      const es = new MockEventSource('/api/test')

      await vi.advanceTimersByTimeAsync(10)

      es.close()

      expect(es.readyState).toBe(MockEventSource.CLOSED)
    })

    it('tracks close calls', async () => {
      const es = new MockEventSource('/api/test')

      await vi.advanceTimersByTimeAsync(10)

      es.close()
      es.close()

      expect(es.close).toHaveBeenCalledTimes(2)
    })

    it('handles done flag in log streaming', async () => {
      const es = new MockEventSource('/api/workflows/123/logs/stream')
      let isDone = false

      es.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.done) {
          isDone = true
          es.close()
        }
      }

      await vi.advanceTimersByTimeAsync(10)

      es.simulateMessage({ content: 'Final log\n', done: true })

      expect(isDone).toBe(true)
      expect(es.close).toHaveBeenCalled()
    })
  })

  describe('Workflow Completion', () => {
    it('sends completion status', async () => {
      const es = new MockEventSource('/api/workflows/123/status/stream')
      let finalStatus: typeof workflowStatuses.completed | null = null

      es.onmessage = (event) => {
        finalStatus = JSON.parse(event.data)
      }

      await vi.advanceTimersByTimeAsync(10)

      es.simulateMessage(workflowStatuses.completed)

      expect(finalStatus?.stage).toBe('completed')
      expect(finalStatus?.progress.current).toBe(100)
      expect(finalStatus?.steps).toBeDefined()
    })

    it('includes step results on completion', async () => {
      const es = new MockEventSource('/api/workflows/123/status/stream')
      let steps: typeof workflowStatuses.completed.steps | null = null

      es.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.steps) {
          steps = data.steps
        }
      }

      await vi.advanceTimersByTimeAsync(10)

      es.simulateMessage(workflowStatuses.completed)

      expect(steps).toHaveLength(3)
      expect(steps?.[0].name).toBe('fetch')
      expect(steps?.[0].success).toBe(95)
    })
  })

  describe('Instance Management', () => {
    it('clears all instances', () => {
      new MockEventSource('/api/stream1')
      new MockEventSource('/api/stream2')

      expect(MockEventSource.instances).toHaveLength(2)

      MockEventSource.clearInstances()

      expect(MockEventSource.instances).toHaveLength(0)
    })

    it('finds instance by URL pattern', () => {
      new MockEventSource('/api/workflows/123/status/stream')
      new MockEventSource('/api/workflows/123/logs/stream')

      const statusStream = MockEventSource.instances.find((es) =>
        es.url.includes('/status/stream')
      )
      const logsStream = MockEventSource.instances.find((es) =>
        es.url.includes('/logs/stream')
      )

      expect(statusStream).toBeDefined()
      expect(logsStream).toBeDefined()
      expect(statusStream).not.toBe(logsStream)
    })
  })

  describe('Real-time Simulation', () => {
    it('simulates real-time status updates', async () => {
      const es = new MockEventSource('/api/workflows/123/status/stream')
      const updates: Array<{ stage: string; timestamp: number }> = []
      const startTime = Date.now()

      es.onmessage = (event) => {
        const data = JSON.parse(event.data)
        updates.push({
          stage: data.stage,
          timestamp: Date.now() - startTime,
        })
      }

      await vi.advanceTimersByTimeAsync(10)

      // Simulate updates over time
      es.simulateMessage({ stage: 'fetching', progress: { current: 0, total: 100 } })
      await vi.advanceTimersByTimeAsync(500)

      es.simulateMessage({ stage: 'fetching', progress: { current: 50, total: 100 } })
      await vi.advanceTimersByTimeAsync(500)

      es.simulateMessage({ stage: 'saving', progress: { current: 0, total: 50 } })

      expect(updates).toHaveLength(3)
    })

    it('simulates log accumulation', async () => {
      const es = new MockEventSource('/api/workflows/123/logs/stream')
      let accumulatedLogs = ''

      es.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.content) {
          accumulatedLogs += data.content
        }
      }

      await vi.advanceTimersByTimeAsync(10)

      // Simulate log chunks arriving
      for (let i = 1; i <= 5; i++) {
        es.simulateMessage({ content: `[10:30:0${i}] Processing item ${i}\n` })
        await vi.advanceTimersByTimeAsync(100)
      }

      expect(accumulatedLogs.split('\n').filter(Boolean)).toHaveLength(5)
    })
  })
})
