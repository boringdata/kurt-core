import { useState, useEffect, useCallback, useRef } from 'react'
import { Type, Shapes, Move, Maximize2, Trash2, Send, X, RefreshCw } from 'lucide-react'
import TextOverlayPopover from './TextOverlayPopover'
import ShapePicker from './ShapePicker'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

/**
 * Shared toolbar for intent capture across media panels.
 * Collects editing intents (add text, add shape, move, resize, delete)
 * and dispatches them to the agent when the user clicks Apply.
 *
 * Props:
 *   workflowId: string - DBOS workflow ID
 *   pageId: string - Page identifier
 *   pageType: string - 'motion-canvas' | 'video' | 'image' | 'video-sequence'
 *   onRefresh: () => void - Called after edits dispatched (to refresh preview)
 *   disabled: boolean - Disable all controls
 */
export default function IntentToolbar({ workflowId, pageId, pageType, onRefresh, disabled = false }) {
  const [mode, setMode] = useState(null) // null | 'text' | 'shape' | 'select'
  const [intents, setIntents] = useState([])
  const [showShapePicker, setShowShapePicker] = useState(false)
  const [showTextPopover, setShowTextPopover] = useState(false)
  const [textPopoverPos, setTextPopoverPos] = useState(null)
  const [pendingShape, setPendingShape] = useState(null)
  const [isDispatching, setIsDispatching] = useState(false)
  const [fonts, setFonts] = useState([])

  // Load available fonts
  useEffect(() => {
    fetch(apiUrl('/api/assets/fonts'))
      .then((r) => r.json())
      .then((d) => setFonts(d.fonts || []))
      .catch(() => {})
  }, [])

  const addIntent = useCallback((intent) => {
    setIntents((prev) => [...prev, intent])
  }, [])

  const removeIntent = useCallback((idx) => {
    setIntents((prev) => prev.filter((_, i) => i !== idx))
  }, [])

  const clearIntents = useCallback(() => {
    setIntents([])
    setMode(null)
    setShowShapePicker(false)
    setShowTextPopover(false)
    setPendingShape(null)
  }, [])

  // Handle canvas/preview click for placement
  const handlePreviewClick = useCallback((e) => {
    if (!mode) return
    const rect = e.currentTarget.getBoundingClientRect()
    const x = Math.round(e.clientX - rect.left)
    const y = Math.round(e.clientY - rect.top)

    if (mode === 'text') {
      setTextPopoverPos({ x, y })
      setShowTextPopover(true)
    } else if (mode === 'shape' && pendingShape) {
      addIntent({
        action: 'add_shape',
        shape_id: pendingShape.shape_id,
        position: { x, y },
        size: { width: 100, height: 100 },
        animated: pendingShape.animated,
      })
      setPendingShape(null)
      setMode(null)
    }
  }, [mode, pendingShape, addIntent])

  const handleTextConfirm = useCallback((textData) => {
    addIntent({
      action: 'add_text',
      text: textData.text,
      position: textPopoverPos,
      style: textData.style,
    })
    setShowTextPopover(false)
    setTextPopoverPos(null)
    setMode(null)
  }, [textPopoverPos, addIntent])

  const handleShapeSelect = useCallback((shapeData) => {
    setPendingShape(shapeData)
    setShowShapePicker(false)
    setMode('shape')
  }, [])

  const handleDispatch = useCallback(async () => {
    if (intents.length === 0 || !workflowId || !pageId) return
    setIsDispatching(true)
    try {
      const res = await fetch(
        apiUrl(`/api/workflows/${workflowId}/pages/${pageId}/edit`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ intents }),
        }
      )
      if (!res.ok) throw new Error(`Dispatch failed: ${res.status}`)
      clearIntents()
      if (onRefresh) onRefresh()
    } catch (err) {
      console.error('Edit dispatch failed:', err)
    } finally {
      setIsDispatching(false)
    }
  }, [intents, workflowId, pageId, clearIntents, onRefresh])

  const intentSummary = (intent) => {
    switch (intent.action) {
      case 'add_text': return `Text: "${intent.text}" at (${intent.position?.x}, ${intent.position?.y})`
      case 'add_shape': return `Shape: ${intent.shape_id} at (${intent.position?.x}, ${intent.position?.y})`
      case 'move_element': return `Move: ${intent.element_id}`
      case 'resize_element': return `Resize: ${intent.element_id}`
      case 'delete_element': return `Delete: ${intent.element_id}`
      default: return intent.action
    }
  }

  return (
    <div className="it-toolbar">
      <div className="it-toolbar-row">
        <div className="it-tools">
          <button
            type="button"
            className={`it-tool-btn ${mode === 'text' ? 'it-tool-active' : ''}`}
            onClick={() => setMode(mode === 'text' ? null : 'text')}
            disabled={disabled}
            title="Add text - click on preview to place"
          >
            <Type size={14} />
            <span>Text</span>
          </button>

          <button
            type="button"
            className={`it-tool-btn ${mode === 'shape' || showShapePicker ? 'it-tool-active' : ''}`}
            onClick={() => {
              if (showShapePicker) {
                setShowShapePicker(false)
                setMode(null)
              } else {
                setShowShapePicker(true)
              }
            }}
            disabled={disabled}
            title="Add shape from library"
          >
            <Shapes size={14} />
            <span>Shape</span>
          </button>
        </div>

        {mode && (
          <div className="it-mode-indicator">
            {mode === 'text' && 'Click on preview to place text'}
            {mode === 'shape' && pendingShape && `Click to place "${pendingShape.title}"`}
            {mode === 'shape' && !pendingShape && 'Select a shape...'}
            <button type="button" className="it-cancel-mode" onClick={() => { setMode(null); setPendingShape(null) }}>
              <X size={12} />
            </button>
          </div>
        )}

        {intents.length > 0 && (
          <div className="it-actions">
            <span className="it-count">{intents.length} edit{intents.length > 1 ? 's' : ''}</span>
            <button
              type="button"
              className="it-apply-btn"
              onClick={handleDispatch}
              disabled={isDispatching}
              title="Send edits to agent"
            >
              {isDispatching ? <RefreshCw size={14} className="it-spinning" /> : <Send size={14} />}
              Apply
            </button>
            <button type="button" className="it-clear-btn" onClick={clearIntents} title="Clear all edits">
              <Trash2 size={12} />
            </button>
          </div>
        )}
      </div>

      {/* Pending intents list */}
      {intents.length > 0 && (
        <div className="it-intents-list">
          {intents.map((intent, idx) => (
            <div key={idx} className="it-intent-chip">
              <span className="it-intent-text">{intentSummary(intent)}</span>
              <button type="button" className="it-intent-remove" onClick={() => removeIntent(idx)}>
                <X size={10} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Shape picker dropdown */}
      {showShapePicker && (
        <ShapePicker
          onSelect={handleShapeSelect}
          onClose={() => setShowShapePicker(false)}
        />
      )}

      {/* Text popover (positioned at click point) */}
      {showTextPopover && (
        <TextOverlayPopover
          position={textPopoverPos}
          fonts={fonts}
          onConfirm={handleTextConfirm}
          onCancel={() => { setShowTextPopover(false); setTextPopoverPos(null); setMode(null) }}
        />
      )}
    </div>
  )
}

/**
 * Hook to wire IntentToolbar's click handler to a preview container.
 * Returns a ref and the click handler to attach to the preview area.
 */
export function useIntentCapture(toolbarRef) {
  // The toolbar exposes handlePreviewClick which panels should call
  // when the preview area is clicked during an active mode.
  return { handlePreviewClick: toolbarRef?.current?.handlePreviewClick }
}
