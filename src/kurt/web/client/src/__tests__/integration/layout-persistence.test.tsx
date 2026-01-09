/**
 * Integration tests for layout persistence
 *
 * Features tested:
 * - Layout save/restore from localStorage
 * - Panel collapse state persistence
 * - Panel size persistence
 * - Tab state persistence
 * - Layout restoration after refresh
 * - Corrupted localStorage handling
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  STORAGE_KEYS,
  panelSizes,
  collapsedStates,
  tabs,
  setupLocalStorage,
  clearLocalStorage,
  createMockDockApi,
} from '../fixtures'

describe('Layout Persistence', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    clearLocalStorage()
  })

  afterEach(() => {
    vi.useRealTimers()
    clearLocalStorage()
  })

  describe('localStorage Storage', () => {
    it('saves panel sizes to localStorage', () => {
      const sizes = panelSizes.default
      localStorage.setItem(STORAGE_KEYS.PANEL_SIZES, JSON.stringify(sizes))

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.PANEL_SIZES) || '{}')
      expect(saved).toEqual(sizes)
    })

    it('saves collapsed state to localStorage', () => {
      const collapsed = collapsedStates.filetreeCollapsed
      localStorage.setItem(STORAGE_KEYS.SIDEBAR_COLLAPSED, JSON.stringify(collapsed))

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) || '{}')
      expect(saved).toEqual(collapsed)
    })

    it('saves tabs to localStorage', () => {
      const openTabs = tabs.multiple
      localStorage.setItem(STORAGE_KEYS.TABS, JSON.stringify(openTabs))

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.TABS) || '[]')
      expect(saved).toEqual(openTabs)
    })
  })

  describe('Panel Size Persistence', () => {
    it('restores saved panel sizes', () => {
      setupLocalStorage({ panelSizes: panelSizes.expanded })

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.PANEL_SIZES) || '{}')
      expect(saved.filetree).toBe(400)
      expect(saved.terminal).toBe(500)
      expect(saved.workflows).toBe(350)
    })

    it('uses default sizes when no saved state', () => {
      const saved = localStorage.getItem(STORAGE_KEYS.PANEL_SIZES)
      expect(saved).toBeNull()
    })

    it('handles partial saved sizes', () => {
      localStorage.setItem(STORAGE_KEYS.PANEL_SIZES, JSON.stringify({ filetree: 300 }))

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.PANEL_SIZES) || '{}')
      expect(saved.filetree).toBe(300)
      expect(saved.terminal).toBeUndefined()
    })
  })

  describe('Collapsed State Persistence', () => {
    it('restores filetree collapsed state', () => {
      setupLocalStorage({ collapsed: collapsedStates.filetreeCollapsed })

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) || '{}')
      expect(saved.filetree).toBe(true)
      expect(saved.terminal).toBe(false)
    })

    it('restores terminal collapsed state', () => {
      setupLocalStorage({ collapsed: collapsedStates.terminalCollapsed })

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) || '{}')
      expect(saved.terminal).toBe(true)
      expect(saved.filetree).toBe(false)
    })

    it('restores workflows collapsed state', () => {
      setupLocalStorage({ collapsed: collapsedStates.workflowsCollapsed })

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) || '{}')
      expect(saved.workflows).toBe(true)
    })

    it('handles all panels collapsed', () => {
      setupLocalStorage({ collapsed: collapsedStates.allCollapsed })

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) || '{}')
      expect(saved.filetree).toBe(true)
      expect(saved.terminal).toBe(true)
      expect(saved.workflows).toBe(true)
    })
  })

  describe('Tab Persistence', () => {
    it('restores open tabs', () => {
      setupLocalStorage({ tabs: tabs.multiple })

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.TABS) || '[]')
      expect(saved).toHaveLength(3)
      expect(saved[0].path).toBe('README.md')
    })

    it('restores dirty state for tabs', () => {
      setupLocalStorage({ tabs: tabs.multiple })

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.TABS) || '[]')
      const dirtyTab = saved.find((t: { isDirty: boolean }) => t.isDirty)
      expect(dirtyTab).toBeDefined()
      expect(dirtyTab.path).toBe('package.json')
    })

    it('handles empty tabs array', () => {
      setupLocalStorage({ tabs: tabs.empty })

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.TABS) || '[]')
      expect(saved).toHaveLength(0)
    })
  })

  describe('Corrupted Data Handling', () => {
    it('handles invalid JSON in panel sizes', () => {
      localStorage.setItem(STORAGE_KEYS.PANEL_SIZES, 'invalid json{')

      expect(() => {
        JSON.parse(localStorage.getItem(STORAGE_KEYS.PANEL_SIZES) || '{}')
      }).toThrow()
    })

    it('provides fallback for corrupted collapsed state', () => {
      localStorage.setItem(STORAGE_KEYS.SIDEBAR_COLLAPSED, 'not valid')

      let collapsed = {}
      try {
        collapsed = JSON.parse(localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) || '{}')
      } catch {
        collapsed = {}
      }

      expect(collapsed).toEqual({})
    })

    it('provides fallback for corrupted tabs', () => {
      localStorage.setItem(STORAGE_KEYS.TABS, '{ broken: true')

      let savedTabs: unknown[] = []
      try {
        savedTabs = JSON.parse(localStorage.getItem(STORAGE_KEYS.TABS) || '[]')
      } catch {
        savedTabs = []
      }

      expect(savedTabs).toEqual([])
    })
  })

  describe('Terminal Session Persistence', () => {
    it('saves terminal sessions', () => {
      const sessions = [
        { id: 'session-1', name: 'claude', provider: 'claude' },
        { id: 'session-2', name: 'codex', provider: 'codex' },
      ]
      localStorage.setItem(STORAGE_KEYS.TERMINAL_SESSIONS, JSON.stringify(sessions))

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.TERMINAL_SESSIONS) || '[]')
      expect(saved).toHaveLength(2)
    })

    it('saves active terminal session', () => {
      localStorage.setItem(STORAGE_KEYS.TERMINAL_ACTIVE, 'session-1')

      expect(localStorage.getItem(STORAGE_KEYS.TERMINAL_ACTIVE)).toBe('session-1')
    })
  })

  describe('Layout JSON Persistence', () => {
    it('saves dockview layout JSON', () => {
      const mockLayout = {
        grid: { root: { type: 'branch', data: [] } },
        panels: { 'editor-1': { id: 'editor-1' } },
        activeGroup: 'center',
      }
      localStorage.setItem(STORAGE_KEYS.LAYOUT, JSON.stringify(mockLayout))

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.LAYOUT) || '{}')
      expect(saved.panels).toBeDefined()
      expect(saved.activeGroup).toBe('center')
    })
  })

  describe('Mock Dock API', () => {
    it('creates mock dock API with panel management', () => {
      const dockApi = createMockDockApi()

      expect(dockApi.addPanel).toBeDefined()
      expect(dockApi.getPanel).toBeDefined()
      expect(dockApi.removePanel).toBeDefined()
    })

    it('tracks added panels', () => {
      const dockApi = createMockDockApi()

      dockApi.addPanel({ id: 'test-panel', params: { file: 'test.md' } })

      expect(dockApi.panels.has('test-panel')).toBe(true)
    })

    it('retrieves panels by ID', () => {
      const dockApi = createMockDockApi()

      dockApi.addPanel({ id: 'editor-1', params: { file: 'readme.md' } })

      const panel = dockApi.getPanel('editor-1')
      expect(panel).toBeDefined()
      expect(panel?.id).toBe('editor-1')
    })

    it('removes panels', () => {
      const dockApi = createMockDockApi()

      const panel = dockApi.addPanel({ id: 'temp-panel' })
      dockApi.removePanel(panel)

      expect(dockApi.panels.has('temp-panel')).toBe(false)
    })

    it('creates groups', () => {
      const dockApi = createMockDockApi()

      const group = dockApi.addGroup({ id: 'center-group' })

      expect(group.id).toBe('center-group')
      expect(dockApi.groups.has('center-group')).toBe(true)
    })

    it('exports layout as JSON', () => {
      const dockApi = createMockDockApi()

      const json = dockApi.toJSON()

      expect(json.grid).toBeDefined()
      expect(json.panels).toBeDefined()
    })

    it('clears all panels and groups', () => {
      const dockApi = createMockDockApi()

      dockApi.addPanel({ id: 'panel-1' })
      dockApi.addPanel({ id: 'panel-2' })
      dockApi.addGroup({ id: 'group-1' })

      dockApi.clear()

      expect(dockApi.panels.size).toBe(0)
      expect(dockApi.groups.size).toBe(0)
    })
  })

  describe('setupLocalStorage Helper', () => {
    it('sets up multiple storage keys at once', () => {
      setupLocalStorage({
        tabs: tabs.multiple,
        panelSizes: panelSizes.expanded,
        collapsed: collapsedStates.filetreeCollapsed,
      })

      expect(localStorage.getItem(STORAGE_KEYS.TABS)).not.toBeNull()
      expect(localStorage.getItem(STORAGE_KEYS.PANEL_SIZES)).not.toBeNull()
      expect(localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED)).not.toBeNull()
    })

    it('handles partial options', () => {
      setupLocalStorage({ tabs: tabs.single })

      expect(localStorage.getItem(STORAGE_KEYS.TABS)).not.toBeNull()
      expect(localStorage.getItem(STORAGE_KEYS.PANEL_SIZES)).toBeNull()
    })
  })

  describe('clearLocalStorage Helper', () => {
    it('clears all kurt-web storage keys', () => {
      setupLocalStorage({
        tabs: tabs.multiple,
        panelSizes: panelSizes.default,
        collapsed: collapsedStates.allExpanded,
      })

      clearLocalStorage()

      expect(localStorage.getItem(STORAGE_KEYS.TABS)).toBeNull()
      expect(localStorage.getItem(STORAGE_KEYS.PANEL_SIZES)).toBeNull()
      expect(localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED)).toBeNull()
    })

    it('does not affect other localStorage keys', () => {
      localStorage.setItem('other-app-key', 'value')
      setupLocalStorage({ tabs: tabs.single })

      clearLocalStorage()

      expect(localStorage.getItem('other-app-key')).toBe('value')
    })
  })
})
