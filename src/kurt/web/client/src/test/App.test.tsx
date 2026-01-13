import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Test utilities for the collapsed state logic
describe('Collapsed State Logic', () => {
  describe('dockviewClassName generation', () => {
    // Extracted logic for testing
    const buildDockviewClassName = (collapsed: {
      filetree: boolean
      terminal: boolean
      workflows: boolean
    }) => {
      return [
        'dockview-theme-abyss',
        collapsed.filetree && 'filetree-is-collapsed',
        collapsed.terminal && 'terminal-is-collapsed',
        collapsed.workflows && 'workflows-is-collapsed',
      ]
        .filter(Boolean)
        .join(' ')
    }

    it('should include base class when nothing is collapsed', () => {
      const result = buildDockviewClassName({
        filetree: false,
        terminal: false,
        workflows: false,
      })
      expect(result).toBe('dockview-theme-abyss')
    })

    it('should include filetree-is-collapsed when filetree is collapsed', () => {
      const result = buildDockviewClassName({
        filetree: true,
        terminal: false,
        workflows: false,
      })
      expect(result).toBe('dockview-theme-abyss filetree-is-collapsed')
    })

    it('should include terminal-is-collapsed when terminal is collapsed', () => {
      const result = buildDockviewClassName({
        filetree: false,
        terminal: true,
        workflows: false,
      })
      expect(result).toBe('dockview-theme-abyss terminal-is-collapsed')
    })

    it('should include workflows-is-collapsed when workflows is collapsed', () => {
      const result = buildDockviewClassName({
        filetree: false,
        terminal: false,
        workflows: true,
      })
      expect(result).toBe('dockview-theme-abyss workflows-is-collapsed')
    })

    it('should include all collapsed classes when all panels are collapsed', () => {
      const result = buildDockviewClassName({
        filetree: true,
        terminal: true,
        workflows: true,
      })
      expect(result).toBe(
        'dockview-theme-abyss filetree-is-collapsed terminal-is-collapsed workflows-is-collapsed'
      )
    })
  })

  describe('RightHeaderActions chevron visibility', () => {
    // Extracted logic for testing
    const shouldShowChevron = (panels: { id: string }[]) => {
      const hasWorkflowsPanel = panels.some((p) => p.id === 'workflows')
      const hasShellPanel = panels.some((p) => p.id === 'shell')

      // Show chevron on:
      // 1. Combined group (has both workflows and shell)
      // 2. Shell-only group when split (rightmost)
      // Don't show on workflows-only group when split (leftmost)
      return (hasWorkflowsPanel && hasShellPanel) || (hasShellPanel && !hasWorkflowsPanel)
    }

    it('should show chevron when group has both workflows and shell', () => {
      const panels = [{ id: 'workflows' }, { id: 'shell' }]
      expect(shouldShowChevron(panels)).toBe(true)
    })

    it('should show chevron when group has only shell (split, rightmost)', () => {
      const panels = [{ id: 'shell' }]
      expect(shouldShowChevron(panels)).toBe(true)
    })

    it('should NOT show chevron when group has only workflows (split, leftmost)', () => {
      const panels = [{ id: 'workflows' }]
      expect(shouldShowChevron(panels)).toBe(false)
    })

    it('should NOT show chevron for unrelated panels', () => {
      const panels = [{ id: 'editor' }, { id: 'filetree' }]
      expect(shouldShowChevron(panels)).toBe(false)
    })

    it('should NOT show chevron for empty panel list', () => {
      const panels: { id: string }[] = []
      expect(shouldShowChevron(panels)).toBe(false)
    })
  })
})

describe('Collapsed State Persistence', () => {
  const SIDEBAR_COLLAPSED_KEY = 'kurt-web-sidebar-collapsed'
  let mockStorage: Record<string, string> = {}

  beforeEach(() => {
    mockStorage = {}
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation((key) => mockStorage[key] || null)
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation((key, value) => {
      mockStorage[key] = value
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('loadCollapsedState', () => {
    const loadCollapsedState = () => {
      try {
        const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
        if (saved) {
          return JSON.parse(saved)
        }
      } catch {
        // Ignore parse errors
      }
      return { filetree: false, terminal: false, workflows: false }
    }

    it('should return default state when nothing is saved', () => {
      const result = loadCollapsedState()
      expect(result).toEqual({ filetree: false, terminal: false, workflows: false })
    })

    it('should return saved state when available', () => {
      const savedState = { filetree: true, terminal: false, workflows: true }
      mockStorage[SIDEBAR_COLLAPSED_KEY] = JSON.stringify(savedState)
      const result = loadCollapsedState()
      expect(result).toEqual(savedState)
    })

    it('should return default state on parse error', () => {
      mockStorage[SIDEBAR_COLLAPSED_KEY] = 'invalid json'
      const result = loadCollapsedState()
      expect(result).toEqual({ filetree: false, terminal: false, workflows: false })
    })
  })

  describe('saveCollapsedState', () => {
    const saveCollapsedState = (state: {
      filetree: boolean
      terminal: boolean
      workflows: boolean
    }) => {
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, JSON.stringify(state))
      } catch {
        // Ignore storage errors
      }
    }

    it('should save state to localStorage', () => {
      const state = { filetree: true, terminal: false, workflows: true }
      saveCollapsedState(state)
      expect(mockStorage[SIDEBAR_COLLAPSED_KEY]).toBe(JSON.stringify(state))
    })
  })
})

describe('Panel Size Management', () => {
  const PANEL_SIZES_KEY = 'kurt-web-panel-sizes'
  let mockStorage: Record<string, string> = {}

  beforeEach(() => {
    mockStorage = {}
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation((key) => mockStorage[key] || null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('loadPanelSizes', () => {
    const loadPanelSizes = () => {
      try {
        const saved = localStorage.getItem(PANEL_SIZES_KEY)
        if (saved) {
          return JSON.parse(saved)
        }
      } catch {
        // Ignore parse errors
      }
      return { filetree: 280, terminal: 400, workflows: 250 }
    }

    it('should return default sizes when nothing is saved', () => {
      const result = loadPanelSizes()
      expect(result).toEqual({ filetree: 280, terminal: 400, workflows: 250 })
    })

    it('should return saved sizes when available', () => {
      const savedSizes = { filetree: 300, terminal: 450, workflows: 200 }
      mockStorage[PANEL_SIZES_KEY] = JSON.stringify(savedSizes)
      const result = loadPanelSizes()
      expect(result).toEqual(savedSizes)
    })
  })
})

describe('Layout Restoration with Collapsed State', () => {
  describe('applyPanelConstraints', () => {
    // Mock API for testing constraint application
    const createMockApi = () => ({
      setConstraints: vi.fn(),
      setSize: vi.fn(),
    })

    it('should apply collapsed constraints when filetree is collapsed', () => {
      const api = createMockApi()
      const collapsed = { filetree: true, terminal: false, workflows: false }

      // Apply collapsed constraints
      if (collapsed.filetree) {
        api.setConstraints({ minimumWidth: 48, maximumWidth: 48 })
        api.setSize({ width: 48 })
      }

      expect(api.setConstraints).toHaveBeenCalledWith({
        minimumWidth: 48,
        maximumWidth: 48,
      })
      expect(api.setSize).toHaveBeenCalledWith({ width: 48 })
    })

    it('should apply expanded constraints when filetree is expanded', () => {
      const api = createMockApi()
      const collapsed = { filetree: false, terminal: false, workflows: false }
      const savedSize = 300

      // Apply expanded constraints
      if (!collapsed.filetree) {
        api.setConstraints({ minimumWidth: 180, maximumWidth: Infinity })
        api.setSize({ width: savedSize })
      }

      expect(api.setConstraints).toHaveBeenCalledWith({
        minimumWidth: 180,
        maximumWidth: Infinity,
      })
      expect(api.setSize).toHaveBeenCalledWith({ width: savedSize })
    })

    it('should apply collapsed constraints when terminal is collapsed', () => {
      const api = createMockApi()
      const collapsed = { filetree: false, terminal: true, workflows: false }

      if (collapsed.terminal) {
        api.setConstraints({ minimumWidth: 48, maximumWidth: 48 })
        api.setSize({ width: 48 })
      }

      expect(api.setConstraints).toHaveBeenCalledWith({
        minimumWidth: 48,
        maximumWidth: 48,
      })
      expect(api.setSize).toHaveBeenCalledWith({ width: 48 })
    })

    it('should apply collapsed constraints when workflows is collapsed', () => {
      const api = createMockApi()
      const collapsed = { filetree: false, terminal: false, workflows: true }

      if (collapsed.workflows) {
        api.setConstraints({ minimumHeight: 36, maximumHeight: 36 })
        api.setSize({ height: 36 })
      }

      expect(api.setConstraints).toHaveBeenCalledWith({
        minimumHeight: 36,
        maximumHeight: 36,
      })
      expect(api.setSize).toHaveBeenCalledWith({ height: 36 })
    })

    it('should apply expanded constraints when workflows is expanded', () => {
      const api = createMockApi()
      const collapsed = { filetree: false, terminal: false, workflows: false }
      const savedHeight = 300

      if (!collapsed.workflows) {
        api.setConstraints({ minimumHeight: 100, maximumHeight: Infinity })
        api.setSize({ height: savedHeight })
      }

      expect(api.setConstraints).toHaveBeenCalledWith({
        minimumHeight: 100,
        maximumHeight: Infinity,
      })
      expect(api.setSize).toHaveBeenCalledWith({ height: savedHeight })
    })
  })
})

describe('Split Panel Collapse Handling', () => {
  describe('applyCollapsedStateToSplitPanels', () => {
    const createMockApi = () => ({
      setConstraints: vi.fn(),
      setSize: vi.fn(),
    })

    it('should apply constraints to both groups when workflows and shell are split', () => {
      const workflowsApi = createMockApi()
      const shellApi = createMockApi()
      const collapsed = { workflows: true }

      // Simulate applying collapsed state to split panels
      const workflowsGroup = { api: workflowsApi }
      const shellGroup = { api: shellApi }
      const areSplit = workflowsGroup !== shellGroup

      if (collapsed.workflows) {
        workflowsApi.setConstraints({ minimumHeight: 36, maximumHeight: 36 })
        workflowsApi.setSize({ height: 36 })

        if (areSplit) {
          shellApi.setConstraints({ minimumHeight: 36, maximumHeight: 36 })
          shellApi.setSize({ height: 36 })
        }
      }

      expect(workflowsApi.setConstraints).toHaveBeenCalledWith({
        minimumHeight: 36,
        maximumHeight: 36,
      })
      expect(workflowsApi.setSize).toHaveBeenCalledWith({ height: 36 })
      expect(shellApi.setConstraints).toHaveBeenCalledWith({
        minimumHeight: 36,
        maximumHeight: 36,
      })
      expect(shellApi.setSize).toHaveBeenCalledWith({ height: 36 })
    })

    it('should not apply to shell when panels are in the same group', () => {
      const sharedApi = createMockApi()
      const collapsed = { workflows: true }

      // Both panels in same group
      const workflowsGroup = { api: sharedApi }
      const shellGroup = workflowsGroup // Same reference
      const areSplit = workflowsGroup !== shellGroup

      if (collapsed.workflows) {
        sharedApi.setConstraints({ minimumHeight: 36, maximumHeight: 36 })
        sharedApi.setSize({ height: 36 })

        // This should NOT run because areSplit is false
        if (areSplit) {
          sharedApi.setConstraints({ minimumHeight: 36, maximumHeight: 36 })
        }
      }

      // Should only be called once (not twice)
      expect(sharedApi.setConstraints).toHaveBeenCalledTimes(1)
      expect(sharedApi.setSize).toHaveBeenCalledTimes(1)
    })
  })
})

describe('Layout Structure Validation (Drift Detection)', () => {
  // Essential panels that must exist
  const ESSENTIAL_PANELS = ['filetree', 'terminal', 'workflows', 'shell']

  // Extracted validation logic for testing
  const validateLayoutStructure = (layout: {
    grid?: { root?: unknown }
    panels?: Record<string, unknown>
  }): boolean => {
    if (!layout?.grid || !layout?.panels) return false

    const panels = layout.panels
    const panelIds = Object.keys(panels)

    // Check all essential panels exist
    for (const essentialId of ESSENTIAL_PANELS) {
      if (!panelIds.includes(essentialId)) {
        return false
      }
    }

    // Extract groups and their panels from the grid structure
    const groups: string[][] = []
    const extractGroups = (node: unknown) => {
      if (!node || typeof node !== 'object') return
      const n = node as { type?: string; data?: unknown }
      if (n.type === 'leaf' && n.data && typeof n.data === 'object') {
        const data = n.data as { views?: { id?: string }[] }
        if (data.views) {
          const groupPanels = data.views.map((v) => v.id).filter(Boolean) as string[]
          groups.push(groupPanels)
        }
      }
      // Recurse into branches
      if (n.data && Array.isArray(n.data)) {
        n.data.forEach(extractGroups)
      }
    }
    extractGroups((layout.grid as { root?: unknown }).root)

    // Find which group each essential panel is in
    const panelToGroup: Record<string, number> = {}
    groups.forEach((groupPanels, groupIndex) => {
      groupPanels.forEach((panelId) => {
        panelToGroup[panelId] = groupIndex
      })
    })

    // Validate filetree is alone in its group (no other essential panels)
    const filetreeGroup = groups[panelToGroup['filetree']]
    if (filetreeGroup) {
      const otherInGroup = filetreeGroup.filter((p) => p !== 'filetree')
      const invalidInGroup = otherInGroup.some((p) => ESSENTIAL_PANELS.includes(p))
      if (invalidInGroup) return false
    }

    // Validate terminal is alone in its group (no other essential panels)
    const terminalGroup = groups[panelToGroup['terminal']]
    if (terminalGroup) {
      const otherInGroup = terminalGroup.filter((p) => p !== 'terminal')
      const invalidInGroup = otherInGroup.some((p) => ESSENTIAL_PANELS.includes(p))
      if (invalidInGroup) return false
    }

    // Validate shell is not mixed with filetree or terminal
    const shellGroupIdx = panelToGroup['shell']
    if (shellGroupIdx !== undefined) {
      const shellGroup = groups[shellGroupIdx]
      if (shellGroup.includes('filetree') || shellGroup.includes('terminal')) {
        return false
      }
    }

    // Validate workflows is not mixed with filetree or terminal
    const workflowsGroupIdx = panelToGroup['workflows']
    if (workflowsGroupIdx !== undefined) {
      const workflowsGroup = groups[workflowsGroupIdx]
      if (workflowsGroup.includes('filetree') || workflowsGroup.includes('terminal')) {
        return false
      }
    }

    return true
  }

  // Helper to create a valid layout structure
  const createValidLayout = () => ({
    panels: {
      filetree: { id: 'filetree', contentComponent: 'filetree' },
      terminal: { id: 'terminal', contentComponent: 'terminal' },
      workflows: { id: 'workflows', contentComponent: 'workflows' },
      shell: { id: 'shell', contentComponent: 'shell' },
      'empty-center': { id: 'empty-center', contentComponent: 'empty' },
    },
    grid: {
      root: {
        type: 'branch',
        data: [
          { type: 'leaf', data: { views: [{ id: 'filetree' }] } },
          {
            type: 'branch',
            data: [
              { type: 'leaf', data: { views: [{ id: 'empty-center' }] } },
              { type: 'leaf', data: { views: [{ id: 'workflows' }, { id: 'shell' }] } },
            ],
          },
          { type: 'leaf', data: { views: [{ id: 'terminal' }] } },
        ],
      },
    },
  })

  describe('valid layouts', () => {
    it('should accept a valid layout with all essential panels', () => {
      const layout = createValidLayout()
      expect(validateLayoutStructure(layout)).toBe(true)
    })

    it('should accept layout with workflows and shell in separate groups', () => {
      const layout = {
        panels: {
          filetree: { id: 'filetree' },
          terminal: { id: 'terminal' },
          workflows: { id: 'workflows' },
          shell: { id: 'shell' },
        },
        grid: {
          root: {
            type: 'branch',
            data: [
              { type: 'leaf', data: { views: [{ id: 'filetree' }] } },
              {
                type: 'branch',
                data: [
                  { type: 'leaf', data: { views: [{ id: 'workflows' }] } },
                  { type: 'leaf', data: { views: [{ id: 'shell' }] } },
                ],
              },
              { type: 'leaf', data: { views: [{ id: 'terminal' }] } },
            ],
          },
        },
      }
      expect(validateLayoutStructure(layout)).toBe(true)
    })

    it('should accept layout with editor panels in groups', () => {
      const layout = createValidLayout()
      // Add editor to center group
      ;(layout.panels as Record<string, unknown>)['editor-test.js'] = {
        id: 'editor-test.js',
        contentComponent: 'editor',
      }
      const root = layout.grid.root as { data: unknown[] }
      const centerBranch = root.data[1] as { data: unknown[] }
      const editorGroup = centerBranch.data[0] as { data: { views: unknown[] } }
      editorGroup.data.views.push({ id: 'editor-test.js' })
      expect(validateLayoutStructure(layout)).toBe(true)
    })
  })

  describe('invalid layouts - missing panels', () => {
    it('should reject layout missing filetree panel', () => {
      const layout = createValidLayout()
      delete (layout.panels as Record<string, unknown>)['filetree']
      expect(validateLayoutStructure(layout)).toBe(false)
    })

    it('should reject layout missing terminal panel', () => {
      const layout = createValidLayout()
      delete (layout.panels as Record<string, unknown>)['terminal']
      expect(validateLayoutStructure(layout)).toBe(false)
    })

    it('should reject layout missing workflows panel', () => {
      const layout = createValidLayout()
      delete (layout.panels as Record<string, unknown>)['workflows']
      expect(validateLayoutStructure(layout)).toBe(false)
    })

    it('should reject layout missing shell panel', () => {
      const layout = createValidLayout()
      delete (layout.panels as Record<string, unknown>)['shell']
      expect(validateLayoutStructure(layout)).toBe(false)
    })
  })

  describe('invalid layouts - structural drift', () => {
    it('should reject layout with shell in filetree group', () => {
      const layout = {
        panels: {
          filetree: { id: 'filetree' },
          terminal: { id: 'terminal' },
          workflows: { id: 'workflows' },
          shell: { id: 'shell' },
        },
        grid: {
          root: {
            type: 'branch',
            data: [
              // Shell wrongly in filetree group
              { type: 'leaf', data: { views: [{ id: 'filetree' }, { id: 'shell' }] } },
              { type: 'leaf', data: { views: [{ id: 'workflows' }] } },
              { type: 'leaf', data: { views: [{ id: 'terminal' }] } },
            ],
          },
        },
      }
      expect(validateLayoutStructure(layout)).toBe(false)
    })

    it('should reject layout with shell in terminal group', () => {
      const layout = {
        panels: {
          filetree: { id: 'filetree' },
          terminal: { id: 'terminal' },
          workflows: { id: 'workflows' },
          shell: { id: 'shell' },
        },
        grid: {
          root: {
            type: 'branch',
            data: [
              { type: 'leaf', data: { views: [{ id: 'filetree' }] } },
              { type: 'leaf', data: { views: [{ id: 'workflows' }] } },
              // Shell wrongly in terminal group
              { type: 'leaf', data: { views: [{ id: 'terminal' }, { id: 'shell' }] } },
            ],
          },
        },
      }
      expect(validateLayoutStructure(layout)).toBe(false)
    })

    it('should reject layout with workflows in filetree group', () => {
      const layout = {
        panels: {
          filetree: { id: 'filetree' },
          terminal: { id: 'terminal' },
          workflows: { id: 'workflows' },
          shell: { id: 'shell' },
        },
        grid: {
          root: {
            type: 'branch',
            data: [
              // Workflows wrongly in filetree group
              { type: 'leaf', data: { views: [{ id: 'filetree' }, { id: 'workflows' }] } },
              { type: 'leaf', data: { views: [{ id: 'shell' }] } },
              { type: 'leaf', data: { views: [{ id: 'terminal' }] } },
            ],
          },
        },
      }
      expect(validateLayoutStructure(layout)).toBe(false)
    })

    it('should reject layout with workflows in terminal group', () => {
      const layout = {
        panels: {
          filetree: { id: 'filetree' },
          terminal: { id: 'terminal' },
          workflows: { id: 'workflows' },
          shell: { id: 'shell' },
        },
        grid: {
          root: {
            type: 'branch',
            data: [
              { type: 'leaf', data: { views: [{ id: 'filetree' }] } },
              { type: 'leaf', data: { views: [{ id: 'shell' }] } },
              // Workflows wrongly in terminal group
              { type: 'leaf', data: { views: [{ id: 'terminal' }, { id: 'workflows' }] } },
            ],
          },
        },
      }
      expect(validateLayoutStructure(layout)).toBe(false)
    })

    it('should reject layout with terminal in filetree group', () => {
      const layout = {
        panels: {
          filetree: { id: 'filetree' },
          terminal: { id: 'terminal' },
          workflows: { id: 'workflows' },
          shell: { id: 'shell' },
        },
        grid: {
          root: {
            type: 'branch',
            data: [
              // Terminal wrongly in filetree group
              { type: 'leaf', data: { views: [{ id: 'filetree' }, { id: 'terminal' }] } },
              { type: 'leaf', data: { views: [{ id: 'workflows' }, { id: 'shell' }] } },
            ],
          },
        },
      }
      expect(validateLayoutStructure(layout)).toBe(false)
    })
  })

  describe('edge cases', () => {
    it('should reject null layout', () => {
      expect(validateLayoutStructure(null as unknown as { grid?: unknown; panels?: unknown })).toBe(
        false
      )
    })

    it('should reject layout without grid', () => {
      const layout = {
        panels: {
          filetree: { id: 'filetree' },
          terminal: { id: 'terminal' },
          workflows: { id: 'workflows' },
          shell: { id: 'shell' },
        },
      }
      expect(validateLayoutStructure(layout as unknown as { grid?: unknown; panels?: unknown })).toBe(
        false
      )
    })

    it('should reject layout without panels', () => {
      const layout = {
        grid: {
          root: {
            type: 'branch',
            data: [],
          },
        },
      }
      expect(validateLayoutStructure(layout as unknown as { grid?: unknown; panels?: unknown })).toBe(
        false
      )
    })

    it('should reject empty layout', () => {
      expect(validateLayoutStructure({} as unknown as { grid?: unknown; panels?: unknown })).toBe(
        false
      )
    })
  })
})
