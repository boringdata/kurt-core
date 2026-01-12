import { useRef, useEffect } from 'react'
import WorkflowList from '../components/WorkflowList'

export default function WorkflowsPanel({ params }) {
  const {
    collapsed,
    onToggleCollapse,
    onAttachWorkflow,
  } = params || {}

  if (collapsed) {
    return (
      <div className="panel-content workflows-panel-content workflows-collapsed">
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={onToggleCollapse}
          title="Expand workflows panel"
          aria-label="Expand workflows panel"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M3.5 6L8 10.5L12.5 6H3.5Z" />
          </svg>
        </button>
        <span className="workflows-collapsed-label">Workflows</span>
      </div>
    )
  }

  return (
    <div className="panel-content workflows-panel-content">
      <div className="workflows-header">
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={onToggleCollapse}
          title="Collapse workflows panel"
          aria-label="Collapse workflows panel"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M3.5 10L8 5.5L12.5 10H3.5Z" />
          </svg>
        </button>
        <div className="workflows-title">
          <span className="status-dot" />
          Workflows
        </div>
      </div>

      <div className="workflows-content">
        <WorkflowList onAttachWorkflow={onAttachWorkflow} />
      </div>
    </div>
  )
}
