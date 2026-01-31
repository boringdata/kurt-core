import { useState, useEffect, useRef } from 'react'
import { X } from 'lucide-react'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

/**
 * Popover for entering text overlay details (text, font, size, color).
 * Used by IntentToolbar when "Add Text" mode is active and user clicks to place.
 */
export default function TextOverlayPopover({ position, onConfirm, onCancel, fonts = [] }) {
  const [text, setText] = useState('')
  const [fontSize, setFontSize] = useState(24)
  const [fontFamily, setFontFamily] = useState('')
  const [color, setColor] = useState('#ffffff')
  const inputRef = useRef(null)

  useEffect(() => {
    if (inputRef.current) inputRef.current.focus()
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!text.trim()) return
    onConfirm({
      text: text.trim(),
      style: {
        font: fontFamily || undefined,
        size: fontSize,
        color,
      },
    })
  }

  return (
    <div
      className="it-text-popover"
      style={{
        left: `${position?.x ?? 0}px`,
        top: `${position?.y ?? 0}px`,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <form onSubmit={handleSubmit} className="it-text-form">
        <div className="it-text-header">
          <span className="it-text-label">Add Text</span>
          <button type="button" className="it-text-close" onClick={onCancel}>
            <X size={12} />
          </button>
        </div>

        <input
          ref={inputRef}
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter text..."
          className="it-text-input"
        />

        <div className="it-text-options">
          <div className="it-text-option">
            <label>Size</label>
            <input
              type="number"
              value={fontSize}
              onChange={(e) => setFontSize(Number(e.target.value) || 24)}
              min={8}
              max={200}
              className="it-text-num"
            />
          </div>

          <div className="it-text-option">
            <label>Color</label>
            <input
              type="color"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              className="it-text-color"
            />
          </div>

          {fonts.length > 0 && (
            <div className="it-text-option it-text-option-wide">
              <label>Font</label>
              <select
                value={fontFamily}
                onChange={(e) => setFontFamily(e.target.value)}
                className="it-text-select"
              >
                <option value="">Default</option>
                {fonts.map((f) => (
                  <option key={f.id || f.family} value={f.family}>
                    {f.family}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div className="it-text-actions">
          <button type="button" className="it-text-cancel" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="it-text-confirm" disabled={!text.trim()}>
            Add
          </button>
        </div>
      </form>
    </div>
  )
}
