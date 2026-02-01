/**
 * Workflow fixtures for testing
 * Based on actual workflow data structures from the application
 */

export interface WorkflowFixture {
  workflow_uuid: string
  name: string
  status: 'PENDING' | 'ENQUEUED' | 'SUCCESS' | 'ERROR' | 'CANCELLED'
  created_at: string
  updated_at: string
  workflow_type?: string
  definition_name?: string
  tokens_in?: number
  tokens_out?: number
  cost_usd?: number
  agent_turns?: number
}

export interface WorkflowStatusFixture {
  stage: string
  progress: {
    current: number
    total: number
  }
  steps?: Array<{
    name: string
    success: number
    error: number
  }>
}

// Base workflow factories
export const createWorkflow = (overrides: Partial<WorkflowFixture> = {}): WorkflowFixture => ({
  workflow_uuid: 'abc12345-1234-5678-9abc-def012345678',
  name: 'fetch',
  status: 'PENDING',
  created_at: '2024-01-15T10:30:00Z',
  updated_at: '2024-01-15T10:30:05Z',
  ...overrides,
})

export const createWorkflowStatus = (overrides: Partial<WorkflowStatusFixture> = {}): WorkflowStatusFixture => ({
  stage: 'fetching',
  progress: {
    current: 5,
    total: 10,
  },
  ...overrides,
})

// Pre-built workflow fixtures
export const workflows = {
  pending: createWorkflow({
    workflow_uuid: 'pending-1234-5678-9abc-def012345678',
    status: 'PENDING',
    name: 'fetch',
  }),

  enqueued: createWorkflow({
    workflow_uuid: 'enqueued-1234-5678-9abc-def012345678',
    status: 'ENQUEUED',
    name: 'map',
  }),

  success: createWorkflow({
    workflow_uuid: 'success-1234-5678-9abc-def012345678',
    status: 'SUCCESS',
    name: 'fetch',
    updated_at: '2024-01-15T10:35:00Z',
  }),

  error: createWorkflow({
    workflow_uuid: 'error-1234-5678-9abc-def012345678',
    status: 'ERROR',
    name: 'fetch',
    updated_at: '2024-01-15T10:32:00Z',
  }),

  cancelled: createWorkflow({
    workflow_uuid: 'cancelled-1234-5678-9abc-def012345678',
    status: 'CANCELLED',
    name: 'map',
  }),

  // Agent workflow with tokens and cost
  agentSuccess: createWorkflow({
    workflow_uuid: 'agent-success-1234-5678-9abc-def012345678',
    status: 'SUCCESS',
    name: 'execute_agent_workflow',
    workflow_type: 'agent',
    definition_name: 'test-agent',
    tokens_in: 50000,
    tokens_out: 1500,
    cost_usd: 0.12,
    agent_turns: 5,
  }),

  agentPending: createWorkflow({
    workflow_uuid: 'agent-pending-1234-5678-9abc-def012345678',
    status: 'PENDING',
    name: 'execute_agent_workflow',
    workflow_type: 'agent',
    definition_name: 'research-agent',
  }),
}

// Workflow status fixtures for different stages
export const workflowStatuses = {
  discovering: createWorkflowStatus({
    stage: 'discovering',
    progress: { current: 3, total: 10 },
  }),

  fetching: createWorkflowStatus({
    stage: 'fetching',
    progress: { current: 25, total: 100 },
  }),

  saving: createWorkflowStatus({
    stage: 'saving',
    progress: { current: 50, total: 100 },
  }),

  embedding: createWorkflowStatus({
    stage: 'embedding',
    progress: { current: 75, total: 100 },
  }),

  persisting: createWorkflowStatus({
    stage: 'persisting',
    progress: { current: 99, total: 100 },
  }),

  completed: createWorkflowStatus({
    stage: 'completed',
    progress: { current: 100, total: 100 },
    steps: [
      { name: 'fetch', success: 95, error: 5 },
      { name: 'save', success: 95, error: 0 },
      { name: 'embed', success: 90, error: 5 },
    ],
  }),
}

// Log fixtures
export const workflowLogs = {
  empty: { content: '', total_lines: 0 },
  short: { content: '[10:30:00] Starting fetch workflow...\n[10:30:01] Fetching page 1 of 10\n', total_lines: 2 },
  long: {
    content: Array(50)
      .fill(null)
      .map((_, i) => `[10:30:${String(i).padStart(2, '0')}] Processing item ${i + 1}`)
      .join('\n'),
    total_lines: 50,
  },
}

// Helper to create a list of workflows
export const createWorkflowList = (count: number, statusPattern?: WorkflowFixture['status'][]): WorkflowFixture[] => {
  const statuses: WorkflowFixture['status'][] = statusPattern || ['PENDING', 'SUCCESS', 'ERROR', 'CANCELLED', 'ENQUEUED']
  return Array(count)
    .fill(null)
    .map((_, i) => createWorkflow({
      workflow_uuid: `workflow-${i}-1234-5678-9abc-def012345678`,
      name: i % 2 === 0 ? 'fetch' : 'map',
      status: statuses[i % statuses.length],
      created_at: new Date(Date.now() - i * 60000).toISOString(),
      updated_at: new Date(Date.now() - i * 60000 + 5000).toISOString(),
    }))
}
