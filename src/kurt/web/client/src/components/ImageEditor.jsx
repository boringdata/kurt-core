import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Stage, Layer, Image as KonvaImage, Rect, Circle, Text, Line, Transformer } from 'react-konva'

const apiBase = import.meta.env.VITE_API_URL || ''
const apiUrl = (path) => `${apiBase}${path}`

// Load image from URL or file
const useImage = (src) => {
  const [image, setImage] = useState(null)
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    if (!src) {
      setImage(null)
      setStatus('idle')
      return
    }

    setStatus('loading')
    const img = new window.Image()
    img.crossOrigin = 'anonymous'

    img.onload = () => {
      setImage(img)
      setStatus('loaded')
    }

    img.onerror = () => {
      setImage(null)
      setStatus('error')
    }

    img.src = src
  }, [src])

  return [image, status]
}

// Shape component that can be selected and transformed
const Shape = ({ shapeProps, isSelected, onSelect, onChange }) => {
  const shapeRef = useRef()
  const trRef = useRef()

  useEffect(() => {
    if (isSelected && trRef.current && shapeRef.current) {
      trRef.current.nodes([shapeRef.current])
      trRef.current.getLayer().batchDraw()
    }
  }, [isSelected])

  const ShapeComponent = shapeProps.type === 'circle' ? Circle : Rect

  return (
    <>
      <ShapeComponent
        ref={shapeRef}
        {...shapeProps}
        draggable
        onClick={onSelect}
        onTap={onSelect}
        onDragEnd={(e) => {
          onChange({
            ...shapeProps,
            x: e.target.x(),
            y: e.target.y(),
          })
        }}
        onTransformEnd={(e) => {
          const node = shapeRef.current
          const scaleX = node.scaleX()
          const scaleY = node.scaleY()

          node.scaleX(1)
          node.scaleY(1)

          onChange({
            ...shapeProps,
            x: node.x(),
            y: node.y(),
            width: Math.max(5, node.width() * scaleX),
            height: Math.max(5, node.height() * scaleY),
            rotation: node.rotation(),
          })
        }}
      />
      {isSelected && (
        <Transformer
          ref={trRef}
          boundBoxFunc={(oldBox, newBox) => {
            if (newBox.width < 5 || newBox.height < 5) {
              return oldBox
            }
            return newBox
          }}
        />
      )}
    </>
  )
}

// Text element component
const TextElement = ({ textProps, isSelected, onSelect, onChange }) => {
  const textRef = useRef()
  const trRef = useRef()

  useEffect(() => {
    if (isSelected && trRef.current && textRef.current) {
      trRef.current.nodes([textRef.current])
      trRef.current.getLayer().batchDraw()
    }
  }, [isSelected])

  return (
    <>
      <Text
        ref={textRef}
        {...textProps}
        draggable
        onClick={onSelect}
        onTap={onSelect}
        onDragEnd={(e) => {
          onChange({
            ...textProps,
            x: e.target.x(),
            y: e.target.y(),
          })
        }}
        onTransformEnd={(e) => {
          const node = textRef.current
          onChange({
            ...textProps,
            x: node.x(),
            y: node.y(),
            fontSize: Math.max(8, textProps.fontSize * node.scaleY()),
            rotation: node.rotation(),
          })
          node.scaleX(1)
          node.scaleY(1)
        }}
      />
      {isSelected && (
        <Transformer
          ref={trRef}
          enabledAnchors={['middle-left', 'middle-right']}
          boundBoxFunc={(oldBox, newBox) => {
            newBox.width = Math.max(30, newBox.width)
            return newBox
          }}
        />
      )}
    </>
  )
}

// History state for undo/redo
const MAX_HISTORY = 50

export default function ImageEditor({
  imageSrc,
  onSave,
  onGenerate,
  width = 800,
  height = 600,
}) {
  const [image, imageStatus] = useImage(imageSrc)
  const [shapes, setShapes] = useState([])
  const [texts, setTexts] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [tool, setTool] = useState('select') // select, rect, circle, text, brush
  const [fillColor, setFillColor] = useState('#3b82f6')
  const [strokeColor, setStrokeColor] = useState('#1e40af')
  const [textContent, setTextContent] = useState('Text')
  const [brushSize, setBrushSize] = useState(5)
  const [lines, setLines] = useState([])
  const [isDrawing, setIsDrawing] = useState(false)
  const [filters, setFilters] = useState({
    brightness: 100,
    contrast: 100,
    saturate: 100,
    blur: 0,
    grayscale: 0,
    sepia: 0,
  })
  const [showFilters, setShowFilters] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatePrompt, setGeneratePrompt] = useState('')
  const [showGenerateDialog, setShowGenerateDialog] = useState(false)
  const stageRef = useRef()

  // Build CSS filter string
  const getFilterString = useCallback(() => {
    const { brightness, contrast, saturate, blur, grayscale, sepia } = filters
    return `brightness(${brightness}%) contrast(${contrast}%) saturate(${saturate}%) blur(${blur}px) grayscale(${grayscale}%) sepia(${sepia}%)`
  }, [filters])

  // History for undo/redo
  const [history, setHistory] = useState([{ shapes: [], texts: [], lines: [] }])
  const [historyIndex, setHistoryIndex] = useState(0)

  // Save state to history
  const saveToHistory = useCallback((newShapes, newTexts, newLines) => {
    setHistory((prev) => {
      // Remove any future history if we're not at the end
      const newHistory = prev.slice(0, historyIndex + 1)
      // Add new state
      newHistory.push({ shapes: newShapes, texts: newTexts, lines: newLines || lines })
      // Limit history size
      if (newHistory.length > MAX_HISTORY) {
        newHistory.shift()
        return newHistory
      }
      return newHistory
    })
    setHistoryIndex((prev) => Math.min(prev + 1, MAX_HISTORY - 1))
  }, [historyIndex, lines])

  // Undo
  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1
      setHistoryIndex(newIndex)
      const state = history[newIndex]
      setShapes(state.shapes)
      setTexts(state.texts)
      setLines(state.lines || [])
      setSelectedId(null)
    }
  }, [historyIndex, history])

  // Redo
  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1
      setHistoryIndex(newIndex)
      const state = history[newIndex]
      setShapes(state.shapes)
      setTexts(state.texts)
      setLines(state.lines || [])
      setSelectedId(null)
    }
  }, [historyIndex, history])

  const canUndo = historyIndex > 0
  const canRedo = historyIndex < history.length - 1

  // Brush drawing handlers
  const handleMouseDown = useCallback((e) => {
    if (tool !== 'brush') return
    setIsDrawing(true)
    const pos = e.target.getStage().getPointerPosition()
    setLines([...lines, {
      id: `line-${Date.now()}`,
      points: [pos.x, pos.y],
      stroke: strokeColor,
      strokeWidth: brushSize,
    }])
  }, [tool, lines, strokeColor, brushSize])

  const handleMouseMove = useCallback((e) => {
    if (!isDrawing || tool !== 'brush') return
    const stage = e.target.getStage()
    const point = stage.getPointerPosition()
    setLines((prevLines) => {
      const lastLine = prevLines[prevLines.length - 1]
      if (!lastLine) return prevLines
      // Add point to the last line
      const newLines = prevLines.slice(0, -1)
      newLines.push({
        ...lastLine,
        points: [...lastLine.points, point.x, point.y],
      })
      return newLines
    })
  }, [isDrawing, tool])

  const handleMouseUp = useCallback(() => {
    if (isDrawing && tool === 'brush') {
      setIsDrawing(false)
      // Save to history after drawing is complete
      saveToHistory(shapes, texts, lines)
    }
  }, [isDrawing, tool, shapes, texts, lines, saveToHistory])

  // Calculate image dimensions to fit canvas while maintaining aspect ratio
  const getImageDimensions = useCallback(() => {
    if (!image) return { x: 0, y: 0, width: 0, height: 0 }

    const imgRatio = image.width / image.height
    const canvasRatio = width / height

    let imgWidth, imgHeight, imgX, imgY

    if (imgRatio > canvasRatio) {
      imgWidth = width
      imgHeight = width / imgRatio
      imgX = 0
      imgY = (height - imgHeight) / 2
    } else {
      imgHeight = height
      imgWidth = height * imgRatio
      imgX = (width - imgWidth) / 2
      imgY = 0
    }

    return { x: imgX, y: imgY, width: imgWidth, height: imgHeight }
  }, [image, width, height])

  // Handle stage click
  const handleStageClick = (e) => {
    const clickedOnEmpty = e.target === e.target.getStage()
    if (clickedOnEmpty) {
      setSelectedId(null)
      return
    }

    const pos = e.target.getStage().getPointerPosition()

    if (tool === 'rect') {
      const newShape = {
        id: `rect-${Date.now()}`,
        type: 'rect',
        x: pos.x - 50,
        y: pos.y - 25,
        width: 100,
        height: 50,
        fill: fillColor,
        stroke: strokeColor,
        strokeWidth: 2,
      }
      const newShapes = [...shapes, newShape]
      setShapes(newShapes)
      saveToHistory(newShapes, texts)
      setSelectedId(newShape.id)
      setTool('select')
    } else if (tool === 'circle') {
      const newShape = {
        id: `circle-${Date.now()}`,
        type: 'circle',
        x: pos.x,
        y: pos.y,
        radius: 40,
        fill: fillColor,
        stroke: strokeColor,
        strokeWidth: 2,
      }
      const newShapes = [...shapes, newShape]
      setShapes(newShapes)
      saveToHistory(newShapes, texts)
      setSelectedId(newShape.id)
      setTool('select')
    } else if (tool === 'text') {
      const newText = {
        id: `text-${Date.now()}`,
        type: 'text',
        x: pos.x,
        y: pos.y,
        text: textContent,
        fontSize: 24,
        fill: fillColor,
        fontFamily: 'Arial',
      }
      const newTexts = [...texts, newText]
      setTexts(newTexts)
      saveToHistory(shapes, newTexts)
      setSelectedId(newText.id)
      setTool('select')
    }
  }

  // Delete selected element
  const handleDelete = useCallback(() => {
    if (!selectedId) return
    const newShapes = shapes.filter((s) => s.id !== selectedId)
    const newTexts = texts.filter((t) => t.id !== selectedId)
    setShapes(newShapes)
    setTexts(newTexts)
    saveToHistory(newShapes, newTexts)
    setSelectedId(null)
  }, [selectedId, shapes, texts, saveToHistory])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Skip if typing in an input
      if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') {
        return
      }

      if (e.key === 'Delete' || e.key === 'Backspace') {
        handleDelete()
      }
      // Undo: Ctrl+Z / Cmd+Z
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault()
        handleUndo()
      }
      // Redo: Ctrl+Shift+Z / Cmd+Shift+Z or Ctrl+Y / Cmd+Y
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault()
        handleRedo()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleDelete, handleUndo, handleRedo])

  // Export canvas as image
  const handleExport = useCallback(() => {
    if (!stageRef.current) return
    const uri = stageRef.current.toDataURL()
    const link = document.createElement('a')
    link.download = 'image-export.png'
    link.href = uri
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }, [])

  // Generate image with AI
  const handleGenerate = async () => {
    if (!generatePrompt.trim()) return

    setIsGenerating(true)
    try {
      const response = await fetch(apiUrl('/api/media/generate/image'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: generatePrompt,
          width: 1024,
          height: 1024,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to generate image')
      }

      const data = await response.json()
      if (data.url && onGenerate) {
        onGenerate(data.url)
      }
      setShowGenerateDialog(false)
      setGeneratePrompt('')
    } catch (err) {
      alert(`Generation failed: ${err.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const imgDims = getImageDimensions()

  return (
    <div className="image-editor">
      {/* Toolbar */}
      <div className="image-editor-toolbar">
        {/* Undo/Redo */}
        <div className="toolbar-group">
          <button
            type="button"
            className="tool-btn"
            onClick={handleUndo}
            disabled={!canUndo}
            title="Undo (Ctrl+Z)"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z" />
            </svg>
          </button>
          <button
            type="button"
            className="tool-btn"
            onClick={handleRedo}
            disabled={!canRedo}
            title="Redo (Ctrl+Shift+Z)"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M18.4 10.6C16.55 8.99 14.15 8 11.5 8c-4.65 0-8.58 3.03-9.96 7.22L3.9 16c1.05-3.19 4.05-5.5 7.6-5.5 1.95 0 3.73.72 5.12 1.88L13 16h9V7l-3.6 3.6z" />
            </svg>
          </button>
        </div>

        <div className="toolbar-group">
          <button
            type="button"
            className={`tool-btn ${tool === 'select' ? 'active' : ''}`}
            onClick={() => setTool('select')}
            title="Select"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z" />
            </svg>
          </button>
          <button
            type="button"
            className={`tool-btn ${tool === 'rect' ? 'active' : ''}`}
            onClick={() => setTool('rect')}
            title="Rectangle"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" />
            </svg>
          </button>
          <button
            type="button"
            className={`tool-btn ${tool === 'circle' ? 'active' : ''}`}
            onClick={() => setTool('circle')}
            title="Circle"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="9" />
            </svg>
          </button>
          <button
            type="button"
            className={`tool-btn ${tool === 'text' ? 'active' : ''}`}
            onClick={() => setTool('text')}
            title="Text"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M5 4v3h5.5v12h3V7H19V4H5z" />
            </svg>
          </button>
          <button
            type="button"
            className={`tool-btn ${tool === 'brush' ? 'active' : ''}`}
            onClick={() => setTool('brush')}
            title="Brush"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M7 14c-1.66 0-3 1.34-3 3 0 1.31-1.16 2-2 2 .92 1.22 2.49 2 4 2 2.21 0 4-1.79 4-4 0-1.66-1.34-3-3-3zm13.71-9.37l-1.34-1.34c-.39-.39-1.02-.39-1.41 0L9 12.25 11.75 15l8.96-8.96c.39-.39.39-1.02 0-1.41z" />
            </svg>
          </button>
        </div>

        <div className="toolbar-group">
          <label className="color-picker">
            <span>Fill</span>
            <input
              type="color"
              value={fillColor}
              onChange={(e) => setFillColor(e.target.value)}
            />
          </label>
          <label className="color-picker">
            <span>Stroke</span>
            <input
              type="color"
              value={strokeColor}
              onChange={(e) => setStrokeColor(e.target.value)}
            />
          </label>
        </div>

        {tool === 'brush' && (
          <div className="toolbar-group">
            <label className="brush-size">
              <span>Size: {brushSize}</span>
              <input
                type="range"
                min="1"
                max="50"
                value={brushSize}
                onChange={(e) => setBrushSize(Number(e.target.value))}
              />
            </label>
          </div>
        )}

        <div className="toolbar-group">
          <button
            type="button"
            className={`tool-btn ${showFilters ? 'active' : ''}`}
            onClick={() => setShowFilters(!showFilters)}
            title="Filters"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-1.75 9c0 .23-.02.46-.05.68l1.48 1.16c.13.11.17.3.08.45l-1.4 2.42c-.09.15-.27.21-.43.15l-1.74-.7c-.36.28-.76.51-1.18.69l-.26 1.85c-.03.17-.18.3-.35.3h-2.8c-.17 0-.32-.13-.35-.29l-.26-1.85c-.43-.18-.82-.41-1.18-.69l-1.74.7c-.16.06-.34 0-.43-.15l-1.4-2.42c-.09-.15-.05-.34.08-.45l1.48-1.16c-.03-.23-.05-.46-.05-.69 0-.23.02-.46.05-.68l-1.48-1.16c-.13-.11-.17-.3-.08-.45l1.4-2.42c.09-.15.27-.21.43-.15l1.74.7c.36-.28.76-.51 1.18-.69l.26-1.85c.03-.17.18-.3.35-.3h2.8c.17 0 .32.13.35.29l.26 1.85c.43.18.82.41 1.18.69l1.74-.7c.16-.06.34 0 .43.15l1.4 2.42c.09.15.05.34-.08.45l-1.48 1.16c.03.23.05.46.05.69z" />
              <circle cx="12" cy="12" r="2.5" />
            </svg>
          </button>
        </div>

        {tool === 'text' && (
          <div className="toolbar-group">
            <input
              type="text"
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              placeholder="Text content"
              className="text-input"
            />
          </div>
        )}

        <div className="toolbar-group toolbar-actions">
          {selectedId && (
            <button type="button" className="action-btn danger" onClick={handleDelete}>
              Delete
            </button>
          )}
          <button
            type="button"
            className="action-btn"
            onClick={() => setShowGenerateDialog(true)}
          >
            AI Generate
          </button>
          <button type="button" className="action-btn primary" onClick={handleExport}>
            Export
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="image-editor-canvas">
        {imageStatus === 'loading' && (
          <div className="canvas-loading">Loading image...</div>
        )}
        {imageStatus === 'error' && (
          <div className="canvas-error">Failed to load image</div>
        )}
        <Stage
          ref={stageRef}
          width={width}
          height={height}
          onClick={handleStageClick}
          onTap={handleStageClick}
          onMouseDown={handleMouseDown}
          onMousemove={handleMouseMove}
          onMouseup={handleMouseUp}
          onTouchStart={handleMouseDown}
          onTouchMove={handleMouseMove}
          onTouchEnd={handleMouseUp}
          style={{ background: '#1a1a2e', filter: getFilterString() }}
        >
          <Layer>
            {/* Background image */}
            {image && (
              <KonvaImage
                image={image}
                x={imgDims.x}
                y={imgDims.y}
                width={imgDims.width}
                height={imgDims.height}
              />
            )}

            {/* Shapes */}
            {shapes.map((shape) => (
              <Shape
                key={shape.id}
                shapeProps={shape}
                isSelected={shape.id === selectedId}
                onSelect={() => setSelectedId(shape.id)}
                onChange={(newAttrs) => {
                  setShapes(shapes.map((s) => (s.id === shape.id ? newAttrs : s)))
                }}
              />
            ))}

            {/* Text elements */}
            {texts.map((text) => (
              <TextElement
                key={text.id}
                textProps={text}
                isSelected={text.id === selectedId}
                onSelect={() => setSelectedId(text.id)}
                onChange={(newAttrs) => {
                  setTexts(texts.map((t) => (t.id === text.id ? newAttrs : t)))
                }}
              />
            ))}

            {/* Brush lines */}
            {lines.map((line) => (
              <Line
                key={line.id}
                points={line.points}
                stroke={line.stroke}
                strokeWidth={line.strokeWidth}
                tension={0.5}
                lineCap="round"
                lineJoin="round"
                globalCompositeOperation="source-over"
              />
            ))}
          </Layer>
        </Stage>
      </div>

      {/* Generate Dialog */}
      {showGenerateDialog && (
        <div className="generate-dialog-overlay" onClick={() => setShowGenerateDialog(false)}>
          <div className="generate-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Generate Image with AI</h3>
            <textarea
              value={generatePrompt}
              onChange={(e) => setGeneratePrompt(e.target.value)}
              placeholder="Describe the image you want to generate..."
              rows={4}
              autoFocus
            />
            <div className="dialog-actions">
              <button
                type="button"
                className="action-btn"
                onClick={() => setShowGenerateDialog(false)}
                disabled={isGenerating}
              >
                Cancel
              </button>
              <button
                type="button"
                className="action-btn primary"
                onClick={handleGenerate}
                disabled={isGenerating || !generatePrompt.trim()}
              >
                {isGenerating ? 'Generating...' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filter Panel */}
      {showFilters && (
        <div className="filter-panel">
          <div className="filter-panel-header">
            <h4>Image Filters</h4>
            <button
              type="button"
              className="filter-reset-btn"
              onClick={() => setFilters({
                brightness: 100,
                contrast: 100,
                saturate: 100,
                blur: 0,
                grayscale: 0,
                sepia: 0,
              })}
            >
              Reset
            </button>
          </div>
          <div className="filter-control">
            <label>Brightness: {filters.brightness}%</label>
            <input
              type="range"
              min="0"
              max="200"
              value={filters.brightness}
              onChange={(e) => setFilters({ ...filters, brightness: Number(e.target.value) })}
            />
          </div>
          <div className="filter-control">
            <label>Contrast: {filters.contrast}%</label>
            <input
              type="range"
              min="0"
              max="200"
              value={filters.contrast}
              onChange={(e) => setFilters({ ...filters, contrast: Number(e.target.value) })}
            />
          </div>
          <div className="filter-control">
            <label>Saturation: {filters.saturate}%</label>
            <input
              type="range"
              min="0"
              max="200"
              value={filters.saturate}
              onChange={(e) => setFilters({ ...filters, saturate: Number(e.target.value) })}
            />
          </div>
          <div className="filter-control">
            <label>Blur: {filters.blur}px</label>
            <input
              type="range"
              min="0"
              max="20"
              value={filters.blur}
              onChange={(e) => setFilters({ ...filters, blur: Number(e.target.value) })}
            />
          </div>
          <div className="filter-control">
            <label>Grayscale: {filters.grayscale}%</label>
            <input
              type="range"
              min="0"
              max="100"
              value={filters.grayscale}
              onChange={(e) => setFilters({ ...filters, grayscale: Number(e.target.value) })}
            />
          </div>
          <div className="filter-control">
            <label>Sepia: {filters.sepia}%</label>
            <input
              type="range"
              min="0"
              max="100"
              value={filters.sepia}
              onChange={(e) => setFilters({ ...filters, sepia: Number(e.target.value) })}
            />
          </div>
        </div>
      )}
    </div>
  )
}
