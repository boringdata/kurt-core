/**
 * Layout and panel fixtures for testing dockview integration
 */

// Panel size fixtures
export const panelSizes = {
  default: {
    filetree: 240,
    terminal: 320,
    workflows: 200,
  },

  collapsed: {
    filetree: 40,
    terminal: 40,
    workflows: 40,
  },

  expanded: {
    filetree: 400,
    terminal: 500,
    workflows: 350,
  },

  minimum: {
    filetree: 160,
    terminal: 200,
    workflows: 100,
  },
}

// Collapsed state fixtures
export const collapsedStates = {
  allExpanded: {
    filetree: false,
    terminal: false,
    workflows: false,
  },

  allCollapsed: {
    filetree: true,
    terminal: true,
    workflows: true,
  },

  filetreeCollapsed: {
    filetree: true,
    terminal: false,
    workflows: false,
  },

  terminalCollapsed: {
    filetree: false,
    terminal: true,
    workflows: false,
  },

  workflowsCollapsed: {
    filetree: false,
    terminal: false,
    workflows: true,
  },
}

// localStorage key constants (matching App.jsx)
export const STORAGE_KEYS = {
  TABS: 'kurt-web-tabs',
  LAYOUT: 'kurt-web-layout',
  SIDEBAR_COLLAPSED: 'kurt-web-sidebar-collapsed',
  PANEL_SIZES: 'kurt-web-panel-sizes',
  TERMINAL_SESSIONS: 'kurt-web-terminal-sessions',
  TERMINAL_ACTIVE: 'kurt-web-terminal-active',
}

// Tab fixtures
export const tabs = {
  empty: [],

  single: [{ path: 'README.md', isDirty: false }],

  multiple: [
    { path: 'README.md', isDirty: false },
    { path: 'src/App.jsx', isDirty: false },
    { path: 'package.json', isDirty: true },
  ],

  allDirty: [
    { path: 'file1.js', isDirty: true },
    { path: 'file2.js', isDirty: true },
  ],
}

// Mock dockview API
export const createMockDockApi = () => {
  const panels = new Map()
  const groups = new Map()

  return {
    panels,
    groups,

    addPanel: vi.fn((options) => {
      const panel = {
        id: options.id,
        params: options.params || {},
        api: {
          setSize: vi.fn(),
          setConstraints: vi.fn(),
          updateParameters: vi.fn(),
          width: panelSizes.default.filetree,
          height: panelSizes.default.workflows,
        },
        group: options.position?.referenceGroup || null,
      }
      panels.set(options.id, panel)
      return panel
    }),

    addGroup: vi.fn((options) => {
      const group = {
        id: options?.id || `group-${groups.size}`,
        api: {
          setSize: vi.fn(),
          setConstraints: vi.fn(),
          height: 400,
          width: 600,
        },
        panels: [],
      }
      groups.set(group.id, group)
      return group
    }),

    getPanel: vi.fn((id) => panels.get(id)),

    getGroup: vi.fn((id) => groups.get(id)),

    removePanel: vi.fn((panel) => {
      panels.delete(panel.id)
    }),

    fromJSON: vi.fn(),
    toJSON: vi.fn(() => ({
      grid: { root: { type: 'branch', data: [] } },
      panels: {},
      activeGroup: null,
    })),

    onDidLayoutChange: vi.fn(() => ({ dispose: vi.fn() })),
    onDidActivePanelChange: vi.fn(() => ({ dispose: vi.fn() })),
    onDidRemovePanel: vi.fn(() => ({ dispose: vi.fn() })),

    clear: vi.fn(() => {
      panels.clear()
      groups.clear()
    }),
  }
}

// Terminal session fixtures
export const terminalSessions = {
  empty: [],

  single: [
    {
      id: 'session-1',
      name: 'claude-session',
      provider: 'claude',
      created: '2024-01-15T10:30:00Z',
    },
  ],

  multiple: [
    {
      id: 'session-1',
      name: 'claude-session',
      provider: 'claude',
      created: '2024-01-15T10:30:00Z',
    },
    {
      id: 'session-2',
      name: 'codex-session',
      provider: 'codex',
      created: '2024-01-15T11:00:00Z',
    },
  ],
}

// Helper to set up localStorage with fixtures
export const setupLocalStorage = (options: {
  tabs?: typeof tabs.empty
  panelSizes?: typeof panelSizes.default
  collapsed?: typeof collapsedStates.allExpanded
  sessions?: typeof terminalSessions.empty
  activeSession?: string
  layout?: object
} = {}) => {
  if (options.tabs) {
    localStorage.setItem(STORAGE_KEYS.TABS, JSON.stringify(options.tabs))
  }
  if (options.panelSizes) {
    localStorage.setItem(STORAGE_KEYS.PANEL_SIZES, JSON.stringify(options.panelSizes))
  }
  if (options.collapsed) {
    localStorage.setItem(STORAGE_KEYS.SIDEBAR_COLLAPSED, JSON.stringify(options.collapsed))
  }
  if (options.sessions) {
    localStorage.setItem(STORAGE_KEYS.TERMINAL_SESSIONS, JSON.stringify(options.sessions))
  }
  if (options.activeSession) {
    localStorage.setItem(STORAGE_KEYS.TERMINAL_ACTIVE, options.activeSession)
  }
  if (options.layout) {
    localStorage.setItem(STORAGE_KEYS.LAYOUT, JSON.stringify(options.layout))
  }
}

// Clear specific localStorage keys
export const clearLocalStorage = () => {
  Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key))
}

// Approval/Review fixtures
export const approvals = {
  empty: [],

  single: [
    {
      id: 'approval-1',
      session_id: 'session-1',
      session_name: 'claude-session',
      file_path: 'src/App.jsx',
      diff: `@@ -1,3 +1,4 @@
+// New comment
 import React from 'react';`,
      created_at: '2024-01-15T10:30:00Z',
    },
  ],

  multiple: [
    {
      id: 'approval-1',
      session_id: 'session-1',
      session_name: 'claude-session',
      file_path: 'src/App.jsx',
      diff: '+ added line',
      created_at: '2024-01-15T10:30:00Z',
    },
    {
      id: 'approval-2',
      session_id: 'session-2',
      session_name: 'codex-session',
      file_path: 'src/utils.js',
      diff: '- removed line',
      created_at: '2024-01-15T10:31:00Z',
    },
  ],
}
