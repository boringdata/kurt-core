/**
 * Mock utilities for testing
 * Provides easy-to-use mock factories for API calls, WebSocket, and SSE
 */
import { vi, Mock } from 'vitest'

// Type for fetch response
interface MockFetchResponse {
  ok: boolean
  status: number
  json: () => Promise<unknown>
  text: () => Promise<string>
}

/**
 * Create a mock fetch function with predefined responses
 * Note: Patterns are sorted by length (longest first) to match more specific patterns first
 */
export function createMockFetch(responses: Record<string, unknown | ((url: string) => unknown)> = {}) {
  // Sort patterns by length (longest first) so more specific patterns match first
  const sortedPatterns = Object.keys(responses).sort((a, b) => b.length - a.length)

  const mockFetch = vi.fn(async (url: string, _options?: RequestInit): Promise<MockFetchResponse> => {
    // Find matching response (checking longer/more specific patterns first)
    for (const pattern of sortedPatterns) {
      if (url.includes(pattern)) {
        const response = responses[pattern]
        const data = typeof response === 'function' ? response(url) : response
        return {
          ok: true,
          status: 200,
          json: async () => data,
          text: async () => JSON.stringify(data),
        }
      }
    }

    // Default 404 response
    return {
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Not found' }),
      text: async () => 'Not found',
    }
  })

  return mockFetch
}

/**
 * Create a mock fetch that returns different responses based on call order
 */
export function createSequentialMockFetch(responses: unknown[]) {
  let callIndex = 0
  return vi.fn(async (): Promise<MockFetchResponse> => {
    const response = responses[callIndex] || responses[responses.length - 1]
    callIndex++
    return {
      ok: true,
      status: 200,
      json: async () => response,
      text: async () => JSON.stringify(response),
    }
  })
}

/**
 * Mock EventSource for SSE testing
 */
export class MockEventSource {
  static instances: MockEventSource[] = []
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2

  url: string
  readyState = MockEventSource.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
    // Simulate async connection
    setTimeout(() => this.connect(), 0)
  }

  connect() {
    this.readyState = MockEventSource.OPEN
    this.onopen?.(new Event('open'))
  }

  close = vi.fn(() => {
    this.readyState = MockEventSource.CLOSED
  })

  // Test helpers
  simulateMessage(data: unknown) {
    if (this.readyState !== MockEventSource.OPEN) return
    const event = new MessageEvent('message', { data: JSON.stringify(data) })
    this.onmessage?.(event)
  }

  simulateError() {
    this.onerror?.(new Event('error'))
  }

  static clearInstances() {
    MockEventSource.instances = []
  }

  static getLastInstance(): MockEventSource | undefined {
    return MockEventSource.instances[MockEventSource.instances.length - 1]
  }
}

/**
 * Mock WebSocket for terminal testing
 */
export class MockWebSocket {
  static instances: MockWebSocket[] = []
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  url: string
  readyState = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
    setTimeout(() => this.connect(), 0)
  }

  connect() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }

  send = vi.fn()

  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close'))
  })

  // Test helpers
  simulateMessage(data: string | object) {
    if (this.readyState !== MockWebSocket.OPEN) return
    const message = typeof data === 'string' ? data : JSON.stringify(data)
    this.onmessage?.(new MessageEvent('message', { data: message }))
  }

  simulateClose(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close', { code, reason }))
  }

  simulateError() {
    this.onerror?.(new Event('error'))
  }

  static clearInstances() {
    MockWebSocket.instances = []
  }

  static getLastInstance(): MockWebSocket | undefined {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1]
  }
}

/**
 * Set up mock fetch with common API responses
 * Note: Patterns are sorted by length (longest first) in createMockFetch,
 * so more specific patterns will match before general ones
 */
export function setupApiMocks(overrides: Record<string, unknown> = {}) {
  const defaults: Record<string, unknown> = {
    '/api/tree': { entries: [] },
    '/api/git/status': { available: true, files: {} },
    '/api/workflows': { workflows: [] },
    '/api/file': { content: '' },
    '/api/search': { results: [] },
    '/api/approval': [],
    ...overrides,
  }

  const mockFetch = createMockFetch(defaults)
  vi.stubGlobal('fetch', mockFetch)
  return mockFetch
}

/**
 * Wait for all pending timers and promises
 */
export async function flushPromises() {
  await new Promise((resolve) => setTimeout(resolve, 0))
}

/**
 * Advance timers and flush promises
 */
export async function advanceTimersAndFlush(ms: number) {
  vi.advanceTimersByTime(ms)
  await flushPromises()
}

/**
 * Create a mock for localStorage
 */
export function createMockLocalStorage(initial: Record<string, string> = {}) {
  let store = { ...initial }

  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    get length() {
      return Object.keys(store).length
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  }
}

/**
 * Helper to wait for element to appear
 */
export async function waitForElement(
  container: HTMLElement,
  selector: string,
  timeout = 1000
): Promise<Element | null> {
  const startTime = Date.now()

  while (Date.now() - startTime < timeout) {
    const element = container.querySelector(selector)
    if (element) return element
    await new Promise((resolve) => setTimeout(resolve, 50))
  }

  return null
}

/**
 * Mock console methods for testing
 */
export function mockConsole() {
  const originalConsole = {
    log: console.log,
    warn: console.warn,
    error: console.error,
  }

  const mocks = {
    log: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }

  console.log = mocks.log
  console.warn = mocks.warn
  console.error = mocks.error

  return {
    mocks,
    restore: () => {
      console.log = originalConsole.log
      console.warn = originalConsole.warn
      console.error = originalConsole.error
    },
  }
}
