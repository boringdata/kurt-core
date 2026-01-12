/**
 * User event utilities for testing UI interactions
 */
import { fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Re-export userEvent for convenience
export { userEvent }

/**
 * Create a user event instance with default options
 */
export function createUser() {
  return userEvent.setup({
    advanceTimers: vi.advanceTimersByTime,
  })
}

/**
 * Simulate drag and drop between elements
 */
export function simulateDragDrop(
  source: Element,
  target: Element,
  data: Record<string, string> = {}
) {
  const dataTransfer = {
    data: {} as Record<string, string>,
    setData(type: string, value: string) {
      this.data[type] = value
    },
    getData(type: string) {
      return this.data[type] || data[type] || ''
    },
    effectAllowed: 'move',
    dropEffect: 'move',
  }

  fireEvent.dragStart(source, { dataTransfer })
  fireEvent.dragOver(target, { dataTransfer })
  fireEvent.drop(target, { dataTransfer })
  fireEvent.dragEnd(source, { dataTransfer })
}

/**
 * Simulate resizing a panel by dragging
 */
export function simulateResize(
  handle: Element,
  deltaX: number,
  deltaY: number
) {
  const rect = handle.getBoundingClientRect()
  const startX = rect.left + rect.width / 2
  const startY = rect.top + rect.height / 2

  fireEvent.mouseDown(handle, {
    clientX: startX,
    clientY: startY,
    button: 0,
  })

  fireEvent.mouseMove(document, {
    clientX: startX + deltaX,
    clientY: startY + deltaY,
  })

  fireEvent.mouseUp(document, {
    clientX: startX + deltaX,
    clientY: startY + deltaY,
  })
}

/**
 * Simulate right-click context menu
 */
export function simulateContextMenu(element: Element, position?: { x: number; y: number }) {
  const rect = element.getBoundingClientRect()
  fireEvent.contextMenu(element, {
    clientX: position?.x ?? rect.left + 10,
    clientY: position?.y ?? rect.top + 10,
    button: 2,
  })
}

/**
 * Simulate keyboard shortcuts
 */
export function simulateKeyboardShortcut(
  element: Element | Document,
  key: string,
  modifiers: { ctrl?: boolean; shift?: boolean; alt?: boolean; meta?: boolean } = {}
) {
  const eventInit = {
    key,
    code: key,
    ctrlKey: modifiers.ctrl ?? false,
    shiftKey: modifiers.shift ?? false,
    altKey: modifiers.alt ?? false,
    metaKey: modifiers.meta ?? false,
  }

  fireEvent.keyDown(element, eventInit)
  fireEvent.keyUp(element, eventInit)
}

/**
 * Simulate typing in an input with debounce handling
 */
export async function typeWithDebounce(
  input: Element,
  text: string,
  debounceMs = 300
) {
  const user = createUser()
  await user.type(input, text)
  vi.advanceTimersByTime(debounceMs)
  await Promise.resolve()
}

/**
 * Simulate clicking and waiting for effects
 */
export async function clickAndWait(element: Element, waitMs = 0) {
  const user = createUser()
  await user.click(element)
  if (waitMs > 0) {
    vi.advanceTimersByTime(waitMs)
    await Promise.resolve()
  }
}

/**
 * Simulate expanding/collapsing a collapsible element
 */
export async function toggleCollapsible(element: Element) {
  const user = createUser()
  await user.click(element)
  await Promise.resolve()
}

/**
 * Simulate scrolling
 */
export function simulateScroll(element: Element, scrollTop: number) {
  Object.defineProperty(element, 'scrollTop', {
    writable: true,
    configurable: true,
    value: scrollTop,
  })
  fireEvent.scroll(element)
}

/**
 * Simulate window resize
 */
export function simulateWindowResize(width: number, height: number) {
  Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: width })
  Object.defineProperty(window, 'innerHeight', { writable: true, configurable: true, value: height })
  fireEvent(window, new Event('resize'))
}

/**
 * Wait for animations to complete (useful for transitions)
 */
export async function waitForAnimation(element: Element) {
  await new Promise((resolve) => {
    element.addEventListener('transitionend', resolve, { once: true })
    setTimeout(resolve, 500) // Fallback timeout
  })
}

/**
 * Simulate focusing an element with keyboard navigation
 */
export function simulateTabFocus(container: Element, direction: 'forward' | 'backward' = 'forward') {
  simulateKeyboardShortcut(container, 'Tab', { shift: direction === 'backward' })
}
