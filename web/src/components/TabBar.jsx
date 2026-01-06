import React from 'react'

function GitStatusBadge({ status }) {
  if (!status) return null

  const statusConfig = {
    M: { label: 'M', className: 'git-status-modified', title: 'Modified' },
    U: { label: 'U', className: 'git-status-untracked', title: 'Untracked' },
    A: { label: 'A', className: 'git-status-added', title: 'Added' },
    D: { label: 'D', className: 'git-status-deleted', title: 'Deleted' },
  }

  const config = statusConfig[status]
  if (!config) return null

  return (
    <span className={`tab-git-status ${config.className}`} title={config.title}>
      {config.label}
    </span>
  )
}

export default function TabBar({ tabs, activeTab, gitStatus = {}, onSelect, onClose }) {
  if (tabs.length === 0) return null

  const getFileName = (path) => {
    const parts = path.split('/')
    return parts[parts.length - 1]
  }

  return (
    <div className="tab-bar">
      {tabs.map((tab) => (
        <div
          key={tab.path}
          className={`tab ${tab.path === activeTab ? 'tab-active' : ''}`}
          onClick={() => onSelect(tab.path)}
        >
          <GitStatusBadge status={gitStatus[tab.path]} />
          <span className={`tab-name ${gitStatus[tab.path] ? `tab-name-${gitStatus[tab.path].toLowerCase()}` : ''}`}>
            {getFileName(tab.path)}
            {tab.isDirty ? ' •' : ''}
          </span>
          <button
            type="button"
            className="tab-close"
            onClick={(e) => {
              e.stopPropagation()
              onClose(tab.path)
            }}
            title="Close"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      ))}
    </div>
  )
}
