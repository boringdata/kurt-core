import React, { useEffect, useState } from 'react'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

export default function FileTree({ onOpen }) {
  const [entries, setEntries] = useState([])
  const [expandedDirs, setExpandedDirs] = useState({})
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [gitStatus, setGitStatus] = useState({})

  const fetchDir = (dirPath) => {
    return fetch(apiUrl(`/api/tree?path=${encodeURIComponent(dirPath)}`))
      .then((r) => r.json())
      .then((data) => data.entries || [])
      .catch(() => [])
  }

  const fetchGitStatus = () => {
    fetch(apiUrl('/api/git/status'))
      .then((r) => r.json())
      .then((data) => {
        if (data.available && data.files) {
          setGitStatus(data.files)
        }
      })
      .catch(() => {})
  }

  useEffect(() => {
    fetchDir('.').then(setEntries)
    fetchGitStatus()

    // Refresh git status periodically
    const interval = setInterval(fetchGitStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      setIsSearching(false)
      return
    }

    setIsSearching(true)
    const timeoutId = setTimeout(() => {
      fetch(apiUrl(`/api/search?q=${encodeURIComponent(searchQuery)}`))
        .then((r) => r.json())
        .then((data) => {
          setSearchResults(data.results || [])
          setIsSearching(false)
        })
        .catch(() => {
          setSearchResults([])
          setIsSearching(false)
        })
    }, 200)

    return () => clearTimeout(timeoutId)
  }, [searchQuery])

  const handleClick = async (entry) => {
    if (entry.is_dir) {
      const path = entry.path
      if (expandedDirs[path]) {
        setExpandedDirs((prev) => {
          const next = { ...prev }
          delete next[path]
          return next
        })
      } else {
        const children = await fetchDir(path)
        setExpandedDirs((prev) => ({
          ...prev,
          [path]: children,
        }))
      }
    } else {
      onOpen(entry.path)
    }
  }

  const handleSearchResultClick = (result) => {
    onOpen(result.path)
    setSearchQuery('')
  }

  const getFileStatus = (path) => {
    return gitStatus[path] || null
  }

  const getDirStatus = (dirPath) => {
    // Check if any file in this directory has changes
    const prefix = dirPath + '/'
    for (const filePath of Object.keys(gitStatus)) {
      if (filePath.startsWith(prefix) || filePath === dirPath) {
        return true
      }
    }
    return false
  }

  const renderStatusBadge = (status) => {
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
      <span className={`git-status-badge ${config.className}`} title={config.title}>
        {config.label}
      </span>
    )
  }

  const renderEntries = (items, depth = 0) => {
    return items.map((e) => {
      const fileStatus = e.is_dir ? null : getFileStatus(e.path)
      const dirHasChanges = e.is_dir && getDirStatus(e.path)

      return (
        <React.Fragment key={e.path}>
          <div
            className={`file-item ${dirHasChanges ? 'has-changes' : ''}`}
            style={{ paddingLeft: `${depth * 16 + 8}px` }}
            onClick={() => handleClick(e)}
          >
            <span className="file-item-icon">
              {e.is_dir ? (expandedDirs[e.path] ? '📂' : '📁') : '📄'}
            </span>
            <span className={`file-item-name ${fileStatus ? `file-name-${fileStatus.toLowerCase()}` : ''}`}>{e.name}</span>
            {renderStatusBadge(fileStatus)}
            {dirHasChanges && <span className="dir-changes-dot" title="Contains changes" />}
          </div>
          {e.is_dir && expandedDirs[e.path] && renderEntries(expandedDirs[e.path], depth + 1)}
        </React.Fragment>
      )
    })
  }

  const highlightMatch = (text, query) => {
    if (!query.trim()) return text
    const idx = text.toLowerCase().indexOf(query.toLowerCase())
    if (idx === -1) return text
    return (
      <>
        {text.slice(0, idx)}
        <mark>{text.slice(idx, idx + query.length)}</mark>
        {text.slice(idx + query.length)}
      </>
    )
  }

  return (
    <div className="file-tree">
      <div className="search-box">
        <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input
          type="text"
          className="search-input"
          placeholder="Search files..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button
            type="button"
            className="search-clear"
            onClick={() => setSearchQuery('')}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        )}
      </div>

      {searchQuery.trim() ? (
        <div className="search-results">
          {isSearching ? (
            <div className="search-status">Searching...</div>
          ) : searchResults.length === 0 ? (
            <div className="search-status">No files found</div>
          ) : (
            searchResults.map((result) => (
              <div
                key={result.path}
                className="search-result-item"
                onClick={() => handleSearchResultClick(result)}
              >
                <span className="search-result-name">
                  {highlightMatch(result.name, searchQuery)}
                  {renderStatusBadge(getFileStatus(result.path))}
                </span>
                <span className="search-result-path">{result.dir}</span>
              </div>
            ))
          )}
        </div>
      ) : (
        <>
          <h3 className="file-tree-title">Project</h3>
          <div>{renderEntries(entries)}</div>
        </>
      )}
    </div>
  )
}
