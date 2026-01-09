import React, { useEffect, useState } from 'react'
import GitDiff from './GitDiff'

export default function ApprovalPanel({ request, onFeedbackChange }) {
  const [feedback, setFeedback] = useState('')

  useEffect(() => {
    setFeedback('')
  }, [request?.id])

  useEffect(() => {
    onFeedbackChange?.(feedback)
  }, [feedback, onFeedbackChange])

  if (!request) return null

  return (
    <>
      <div className="approval-feedback">
        <label htmlFor="approval-feedback-input">Feedback (optional)</label>
        <textarea
          id="approval-feedback-input"
          value={feedback}
          onChange={(event) => setFeedback(event.target.value)}
          placeholder="Tell Claude what to adjust before approving."
          rows={2}
        />
      </div>
      <div className="approval-diff">
        <GitDiff diff={request.diff} showFileHeader={false} />
      </div>
    </>
  )
}
