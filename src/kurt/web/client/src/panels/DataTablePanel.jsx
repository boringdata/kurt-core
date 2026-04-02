import { useState, useEffect, useCallback, useRef } from 'react'
import { Plus, Trash2, Play, Save, Download, Upload, ChevronLeft, ChevronRight } from 'lucide-react'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

const ROWS_PER_PAGE = 50

function EditableCell({ value, column, onChange, onCommit }) {
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState(value ?? '')
  const inputRef = useRef(null)

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editing])

  useEffect(() => {
    setEditValue(value ?? '')
  }, [value])

  if (!column.editable) {
    return <span className="dt-cell-readonly">{String(value ?? '')}</span>
  }

  if (!editing) {
    return (
      <span
        className="dt-cell-value"
        onDoubleClick={() => setEditing(true)}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === 'F2') {
            e.preventDefault()
            setEditing(true)
          }
        }}
        role="button"
      >
        {column.type === 'boolean' ? (
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => {
              onChange(e.target.checked)
              onCommit()
            }}
            className="dt-checkbox"
          />
        ) : (
          String(value ?? '')
        )}
      </span>
    )
  }

  const handleBlur = () => {
    setEditing(false)
    if (editValue !== (value ?? '')) {
      let parsed = editValue
      if (column.type === 'number') {
        parsed = editValue === '' ? null : Number(editValue)
      }
      onChange(parsed)
      onCommit()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleBlur()
    } else if (e.key === 'Escape') {
      setEditValue(value ?? '')
      setEditing(false)
    }
  }

  if (column.type === 'select' && column.options) {
    return (
      <select
        ref={inputRef}
        className="dt-cell-select"
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
      >
        <option value="">--</option>
        {column.options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    )
  }

  return (
    <input
      ref={inputRef}
      className="dt-cell-input"
      type={column.type === 'number' ? 'number' : 'text'}
      value={editValue}
      onChange={(e) => setEditValue(e.target.value)}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
    />
  )
}

export default function DataTablePanel({ params }) {
  const {
    workflowId,
    pageId,
    pageConfig,
    onRunWorkflow,
  } = params || {}

  const [columns, setColumns] = useState(pageConfig?.columns || [])
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [isDirty, setIsDirty] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isSeed, setIsSeed] = useState(pageConfig?.seed || false)
  const [showRunPrompt, setShowRunPrompt] = useState(false)

  const fetchData = useCallback(async () => {
    if (!workflowId || !pageId) return
    setIsLoading(true)
    setError(null)
    try {
      const offset = page * ROWS_PER_PAGE
      const response = await fetch(
        apiUrl(`/api/workflows/${workflowId}/pages/${pageId}/data?offset=${offset}&limit=${ROWS_PER_PAGE}`)
      )
      if (!response.ok) throw new Error(`Failed to load: ${response.status}`)
      const data = await response.json()
      if (data.columns?.length > 0) setColumns(data.columns)
      setRows(data.rows || [])
      setTotal(data.total || 0)
      setIsSeed(data.seed || false)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }, [workflowId, pageId, page])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleCellChange = (rowIdx, colName, newValue) => {
    setRows((prev) => {
      const next = [...prev]
      next[rowIdx] = { ...next[rowIdx], [colName]: newValue }
      return next
    })
    setIsDirty(true)
  }

  const handleAddRow = () => {
    const newRow = {}
    columns.forEach((col) => {
      newRow[col.name] = col.type === 'number' ? 0 : col.type === 'boolean' ? false : ''
    })
    setRows((prev) => [...prev, newRow])
    setTotal((prev) => prev + 1)
    setIsDirty(true)
  }

  const handleDeleteRow = (idx) => {
    setRows((prev) => prev.filter((_, i) => i !== idx))
    setTotal((prev) => prev - 1)
    setIsDirty(true)
  }

  const handleSave = async () => {
    if (!workflowId || !pageId) return
    setIsSaving(true)
    try {
      const response = await fetch(
        apiUrl(`/api/workflows/${workflowId}/pages/${pageId}/data`),
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rows }),
        }
      )
      if (!response.ok) throw new Error(`Save failed: ${response.status}`)
      setIsDirty(false)
      if (isSeed) {
        setShowRunPrompt(true)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSaving(false)
    }
  }

  const handleRunWorkflow = async () => {
    setShowRunPrompt(false)
    try {
      const response = await fetch(
        apiUrl(`/api/workflows/${workflowId}/pages/${pageId}/run`),
        { method: 'POST' }
      )
      if (!response.ok) throw new Error(`Run failed: ${response.status}`)
      const data = await response.json()
      onRunWorkflow?.(data.workflow_id)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${pageId}-data.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json,.csv'
    input.onchange = async (e) => {
      const file = e.target.files[0]
      if (!file) return
      const text = await file.text()
      try {
        if (file.name.endsWith('.json')) {
          const data = JSON.parse(text)
          setRows(Array.isArray(data) ? data : data.rows || [])
        } else if (file.name.endsWith('.csv')) {
          const lines = text.split('\n').filter((l) => l.trim())
          if (lines.length < 2) return
          const headers = lines[0].split(',').map((h) => h.trim())
          const imported = lines.slice(1).map((line) => {
            const vals = line.split(',')
            const row = {}
            headers.forEach((h, i) => { row[h] = vals[i]?.trim() ?? '' })
            return row
          })
          setRows(imported)
        }
        setIsDirty(true)
      } catch (err) {
        setError(`Import failed: ${err.message}`)
      }
    }
    input.click()
  }

  const totalPages = Math.ceil(total / ROWS_PER_PAGE)
  const title = pageConfig?.title || 'Data Table'

  return (
    <div className="panel-content dt-panel">
      <div className="dt-toolbar">
        <span className="dt-title">{title}</span>
        {isSeed && <span className="dt-seed-badge">Seed Data</span>}
        <div className="dt-toolbar-actions">
          <button type="button" className="dt-btn" onClick={handleAddRow} title="Add row">
            <Plus size={14} /> Add Row
          </button>
          <button type="button" className="dt-btn" onClick={handleImport} title="Import data">
            <Upload size={14} />
          </button>
          <button type="button" className="dt-btn" onClick={handleExport} title="Export data">
            <Download size={14} />
          </button>
          <button
            type="button"
            className={`dt-btn dt-btn-primary ${isDirty ? 'dt-btn-dirty' : ''}`}
            onClick={handleSave}
            disabled={!isDirty || isSaving}
            title="Save changes"
          >
            <Save size={14} /> {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {showRunPrompt && (
        <div className="dt-run-prompt">
          <span>Seed data updated. Run the workflow with new data?</span>
          <button type="button" className="dt-btn dt-btn-run" onClick={handleRunWorkflow}>
            <Play size={14} /> Run Workflow
          </button>
          <button type="button" className="dt-btn" onClick={() => setShowRunPrompt(false)}>
            Dismiss
          </button>
        </div>
      )}

      {error && <div className="dt-error">{error}</div>}

      {isLoading ? (
        <div className="dt-loading">Loading data...</div>
      ) : (
        <>
          <div className="dt-table-wrapper">
            <table className="dt-table">
              <thead>
                <tr>
                  <th className="dt-row-num">#</th>
                  {columns.map((col) => (
                    <th
                      key={col.name}
                      className="dt-header"
                      style={col.width ? { width: col.width } : undefined}
                    >
                      {col.label || col.name}
                      {col.required && <span className="dt-required">*</span>}
                    </th>
                  ))}
                  <th className="dt-actions-col" />
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIdx) => (
                  <tr key={rowIdx} className="dt-row">
                    <td className="dt-row-num">{page * ROWS_PER_PAGE + rowIdx + 1}</td>
                    {columns.map((col) => (
                      <td key={col.name} className="dt-cell">
                        <EditableCell
                          value={row[col.name]}
                          column={col}
                          onChange={(val) => handleCellChange(rowIdx, col.name, val)}
                          onCommit={() => {}}
                        />
                      </td>
                    ))}
                    <td className="dt-actions-cell">
                      <button
                        type="button"
                        className="dt-delete-btn"
                        onClick={() => handleDeleteRow(rowIdx)}
                        title="Delete row"
                      >
                        <Trash2 size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={columns.length + 2} className="dt-empty">
                      No data. Click "Add Row" to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="dt-pagination">
              <button
                type="button"
                className="dt-btn"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft size={14} />
              </button>
              <span className="dt-page-info">
                Page {page + 1} of {totalPages} ({total} rows)
              </span>
              <button
                type="button"
                className="dt-btn"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
