import { useState, useEffect, useRef, useCallback } from 'react'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

/**
 * Hook that polls a workflow page's metadata for file changes.
 * When the file's mtime changes, triggers a refresh callback.
 *
 * @param {string} workflowId - DBOS workflow ID
 * @param {string} pageId - Page identifier
 * @param {object} options - { interval: poll interval ms (default 2000), enabled: boolean }
 * @returns {{ mtime, isStale, refresh }}
 */
export default function useFileWatch(workflowId, pageId, options = {}) {
  const { interval = 2000, enabled = true } = options
  const [mtime, setMtime] = useState(null)
  const [isStale, setIsStale] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const lastMtime = useRef(null)
  const pollRef = useRef(null)

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1)
    setIsStale(false)
  }, [])

  useEffect(() => {
    if (!enabled || !workflowId || !pageId) return

    const poll = async () => {
      try {
        const res = await fetch(
          apiUrl(`/api/workflows/${workflowId}/pages/${pageId}/data`)
        )
        if (!res.ok) return
        const data = await res.json()
        const newMtime = data.mtime

        if (newMtime && lastMtime.current !== null && newMtime !== lastMtime.current) {
          setIsStale(true)
          setMtime(newMtime)
        } else if (newMtime) {
          setMtime(newMtime)
        }
        lastMtime.current = newMtime
      } catch {
        // Ignore poll errors
      }
    }

    poll()
    pollRef.current = setInterval(poll, interval)

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [workflowId, pageId, interval, enabled, refreshKey])

  return { mtime, isStale, refresh, refreshKey }
}
