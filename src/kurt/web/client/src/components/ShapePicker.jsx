import { useState, useEffect, useCallback } from 'react'
import { X, Search } from 'lucide-react'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

/**
 * Grid browser for the SVG shape library.
 * Loads shapes from /api/assets/shapes manifest and displays thumbnails.
 * User selects a shape, then clicks on the canvas to place it.
 */
export default function ShapePicker({ onSelect, onClose }) {
  const [shapes, setShapes] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')

  const fetchShapes = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await fetch(apiUrl('/api/assets/shapes'))
      if (!res.ok) throw new Error('Failed to load shapes')
      const data = await res.json()
      setShapes(data.shapes || [])
    } catch {
      setShapes([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchShapes()
  }, [fetchShapes])

  const categories = ['all', ...new Set(shapes.map((s) => s.category).filter(Boolean))]

  const filtered = shapes.filter((s) => {
    if (selectedCategory !== 'all' && s.category !== selectedCategory) return false
    if (filter && !s.title?.toLowerCase().includes(filter.toLowerCase()) && !s.id?.toLowerCase().includes(filter.toLowerCase())) return false
    return true
  })

  const handleSelect = (shape) => {
    onSelect({
      shape_id: shape.id,
      animated: shape.animated || false,
      title: shape.title || shape.id,
    })
  }

  return (
    <div className="sp-picker" onClick={(e) => e.stopPropagation()}>
      <div className="sp-header">
        <span className="sp-title">Shapes</span>
        <button type="button" className="sp-close" onClick={onClose}>
          <X size={14} />
        </button>
      </div>

      <div className="sp-search">
        <Search size={12} />
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Search shapes..."
          className="sp-search-input"
        />
      </div>

      {categories.length > 2 && (
        <div className="sp-categories">
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              className={`sp-cat-btn ${selectedCategory === cat ? 'sp-cat-active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      <div className="sp-grid">
        {isLoading ? (
          <div className="sp-loading">Loading shapes...</div>
        ) : filtered.length === 0 ? (
          <div className="sp-empty">
            {shapes.length === 0
              ? 'No shapes available. Add SVGs to assets/shapes/'
              : 'No matching shapes'}
          </div>
        ) : (
          filtered.map((shape) => (
            <button
              key={shape.id}
              type="button"
              className="sp-shape-card"
              onClick={() => handleSelect(shape)}
              title={shape.title || shape.id}
            >
              <div className="sp-shape-preview">
                {shape.svg_path ? (
                  <img
                    src={apiUrl(`/api/file/raw?path=assets/shapes/${shape.svg_path}`)}
                    alt={shape.title || shape.id}
                    className="sp-shape-img"
                  />
                ) : (
                  <div className="sp-shape-placeholder" />
                )}
                {shape.animated && <span className="sp-animated-badge">anim</span>}
              </div>
              <span className="sp-shape-label">{shape.title || shape.id}</span>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
