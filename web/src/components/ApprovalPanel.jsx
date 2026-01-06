import React, { useEffect, useState } from 'react'
import GitDiff from './GitDiff'

export default function ApprovalPanel({ request, onDecision, onOpenFile }) {
  if (!request) return null
  const [feedback, setFeedback] = useState('')
  const displayPath = request.project_path || request.file_path || 'Unknown file'

  useEffect(() => {
    setFeedback('')
  }, [request.id])

  return (
    <div className="approval-panel">
      <div className="approval-header">
        <div>
          <div className="approval-title">Claude wants to edit</div>
          <div className="approval-path">{displayPath}</div>
        </div>
        <div className="approval-actions">
          <button
            type="button"
            className="approval-secondary"
            onClick={() => onOpenFile(displayPath)}
            disabled={!displayPath || displayPath === 'Unknown file'}
          >
            Open file
          </button>
          <button
            type="button"
            className="approval-deny"
            onClick={() => onDecision(request.id, 'deny', feedback)}
          >
            Deny
          </button>
          <button
            type="button"
            className="approval-allow"
            onClick={() => onDecision(request.id, 'allow', feedback)}
          >
            Allow
          </button>
        </div>
      </div>
      <div className="approval-meta">
        <span>Tool: {request.tool_name}</span>
        <span>Status: {request.status}</span>
      </div>
      <div className="approval-feedback">
        <label htmlFor="approval-feedback-input">Feedback (optional)</label>
        <textarea
          id="approval-feedback-input"
          value={feedback}
          onChange={(event) => setFeedback(event.target.value)}
          placeholder="Tell Claude what to adjust before approving."
          rows={3}
        />
      </div>
      <div className="approval-diff">
        <GitDiff diff={request.diff} />
      </div>
    </div>
  )
}
