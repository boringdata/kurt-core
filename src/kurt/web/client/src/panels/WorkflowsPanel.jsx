import { ChevronDown, ChevronUp } from 'lucide-react'
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
          <ChevronDown size={16} />
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
          <ChevronUp size={16} />
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
