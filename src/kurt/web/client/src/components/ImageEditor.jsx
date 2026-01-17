import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Stage, Layer, Image as KonvaImage, Rect, Circle, Text, Transformer } from 'react-konva'

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
  const [tool, setTool] = useState('select') // select, rect, circle, text
  const [fillColor, setFillColor] = useState('#3b82f6')
  const [strokeColor, setStrokeColor] = useState('#1e40af')
  const [textContent, setTextContent] = useState('Text')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatePrompt, setGeneratePrompt] = useState('')
  const [showGenerateDialog, setShowGenerateDialog] = useState(false)
  const stageRef = useRef()

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
      setShapes([...shapes, newShape])
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
      setShapes([...shapes, newShape])
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
      setTexts([...texts, newText])
      setSelectedId(newText.id)
      setTool('select')
    }
  }

  // Delete selected element
  const handleDelete = useCallback(() => {
    if (!selectedId) return
    setShapes(shapes.filter((s) => s.id !== selectedId))
    setTexts(texts.filter((t) => t.id !== selectedId))
    setSelectedId(null)
  }, [selectedId, shapes, texts])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (document.activeElement.tagName !== 'INPUT') {
          handleDelete()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleDelete])

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
          style={{ background: '#1a1a2e' }}
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
    </div>
  )
}
