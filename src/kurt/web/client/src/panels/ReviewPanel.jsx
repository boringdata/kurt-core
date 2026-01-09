import React, { useEffect, useState } from 'react'
import ApprovalPanel from '../components/ApprovalPanel'

const buildMeta = (request) => {
  if (!request) return ''
  const parts = []
  if (request.session_provider) {
    parts.push(request.session_provider)
  }
  if (request.session_name) {
    parts.push(request.session_name)
  }
  if (request.session_id) {
    parts.push(request.session_id.slice(0, 8))
  }
  return parts.join(' | ')
}

export default function ReviewPanel({ params }) {
  const { request, filePath, onDecision, onOpenFile } = params || {}
  const [feedback, setFeedback] = useState('')

  useEffect(() => {
    setFeedback('')
  }, [request?.id])

  if (!request) {
    return (
      <div className="panel-content review-panel-content">
        <div className="approval-panel">
          <div className="approval-header">
            <div className="approval-title">Review no longer pending</div>
          </div>
        </div>
      </div>
    )
  }

  const meta = buildMeta(request)
  const title = request.tool_name ? `Review: ${request.tool_name}` : 'Review'
  const pathLabel = filePath || request.project_path || request.file_path || ''

  return (
    <div className="panel-content review-panel-content">
      <div className="approval-panel">
        <div className="approval-header">
          <div>
            <div className="approval-title">{title}</div>
            {pathLabel && <div className="approval-path">{pathLabel}</div>}
          </div>
          {pathLabel && onOpenFile && (
            <button
              type="button"
              className="approval-secondary"
              onClick={() => onOpenFile(pathLabel)}
            >
              Open file
            </button>
          )}
        </div>
        {meta && <div className="approval-meta">{meta}</div>}
        <ApprovalPanel request={request} onFeedbackChange={setFeedback} />
        <div className="approval-actions">
          <button
            type="button"
            className="approval-deny"
            onClick={() => onDecision?.(request.id, 'deny', feedback)}
          >
            Deny
          </button>
          <button
            type="button"
            className="approval-allow"
            onClick={() => onDecision?.(request.id, 'allow', feedback)}
          >
            Allow
          </button>
        </div>
      </div>
    </div>
  )
}
