import { useMemo } from 'react'

/**
 * WorkflowMetrics - Displays aggregate statistics for a list of workflows.
 *
 * Shows summary cards with:
 * - Total workflow count by status (success/error/running)
 * - Total cost (sum of cost_usd)
 * - Total tokens (sum of tokens_in + tokens_out)
 * - Average duration
 */

const formatTokens = (tokens) => {
  if (tokens == null || tokens === 0) return '0'
  if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`
  return tokens.toLocaleString()
}

const formatCost = (cost) => {
  if (cost == null || cost === 0) return '$0.00'
  if (cost < 0.01) return `$${cost.toFixed(4)}`
  if (cost < 1) return `$${cost.toFixed(3)}`
  return `$${cost.toFixed(2)}`
}

const formatDuration = (ms) => {
  if (ms == null || ms === 0) return '-'
  if (ms < 1000) return `${Math.round(ms)}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)
  return `${minutes}m ${remainingSeconds}s`
}

export default function WorkflowMetrics({ workflows }) {
  const metrics = useMemo(() => {
    if (!workflows || workflows.length === 0) {
      return null
    }

    let successCount = 0
    let errorCount = 0
    let runningCount = 0
    let totalCost = 0
    let totalTokensIn = 0
    let totalTokensOut = 0
    let totalDuration = 0
    let durationCount = 0

    for (const workflow of workflows) {
      // Count by status
      switch (workflow.status) {
        case 'SUCCESS':
          successCount++
          break
        case 'ERROR':
        case 'RETRIES_EXCEEDED':
          errorCount++
          break
        case 'PENDING':
        case 'ENQUEUED':
          runningCount++
          break
        default:
          // CANCELLED and others
          break
      }

      // Aggregate cost
      if (workflow.cost_usd != null && workflow.cost_usd > 0) {
        totalCost += workflow.cost_usd
      }

      // Aggregate tokens
      if (workflow.tokens_in != null) {
        totalTokensIn += workflow.tokens_in
      }
      if (workflow.tokens_out != null) {
        totalTokensOut += workflow.tokens_out
      }

      // Calculate average duration from completed workflows
      if (workflow.duration_ms != null && workflow.duration_ms > 0) {
        totalDuration += workflow.duration_ms
        durationCount++
      }
    }

    const totalTokens = totalTokensIn + totalTokensOut
    const avgDuration = durationCount > 0 ? totalDuration / durationCount : 0

    return {
      total: workflows.length,
      successCount,
      errorCount,
      runningCount,
      totalCost,
      totalTokens,
      totalTokensIn,
      totalTokensOut,
      avgDuration,
    }
  }, [workflows])

  // Don't render if no workflows
  if (!metrics) {
    return null
  }

  return (
    <div className="workflow-metrics">
      <div className="workflow-metrics-card">
        <div className="workflow-metrics-label">Workflows</div>
        <div className="workflow-metrics-value">
          <span className="workflow-metrics-count">{metrics.total}</span>
          <span className="workflow-metrics-breakdown">
            {metrics.successCount > 0 && (
              <span className="workflow-metrics-status workflow-metrics-success">
                {metrics.successCount} ok
              </span>
            )}
            {metrics.errorCount > 0 && (
              <span className="workflow-metrics-status workflow-metrics-error">
                {metrics.errorCount} err
              </span>
            )}
            {metrics.runningCount > 0 && (
              <span className="workflow-metrics-status workflow-metrics-running">
                {metrics.runningCount} run
              </span>
            )}
          </span>
        </div>
      </div>

      {metrics.totalCost > 0 && (
        <div className="workflow-metrics-card">
          <div className="workflow-metrics-label">Total Cost</div>
          <div className="workflow-metrics-value">
            <span className="workflow-metrics-cost">{formatCost(metrics.totalCost)}</span>
          </div>
        </div>
      )}

      {metrics.totalTokens > 0 && (
        <div className="workflow-metrics-card">
          <div className="workflow-metrics-label">Tokens</div>
          <div className="workflow-metrics-value">
            <span className="workflow-metrics-tokens">
              {formatTokens(metrics.totalTokensIn)} in / {formatTokens(metrics.totalTokensOut)} out
            </span>
          </div>
        </div>
      )}

      {metrics.avgDuration > 0 && (
        <div className="workflow-metrics-card">
          <div className="workflow-metrics-label">Avg Duration</div>
          <div className="workflow-metrics-value">
            <span className="workflow-metrics-duration">{formatDuration(metrics.avgDuration)}</span>
          </div>
        </div>
      )}
    </div>
  )
}
