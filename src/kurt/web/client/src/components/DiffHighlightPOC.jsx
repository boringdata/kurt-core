/**
 * POC: Editable diff view with proper line alignment
 * Left panel shows original with deletions highlighted (red)
 * Right panel is editable with additions highlighted (green)
 * Uses row-based layout to ensure left and right have same height
 */
import { useState, useCallback, useRef, useEffect } from 'react'
import { diffLines } from 'diff'

const LINE_HEIGHT = 24

// Build aligned line structure from diff
function buildAlignedLines(originalContent, currentContent) {
  if (originalContent === currentContent) {
    const lines = currentContent.split('\n')
    return lines.map((text, i) => ({
      type: 'normal',
      leftText: text,
      rightText: text,
      leftLineNum: i + 1,
      rightLineNum: i + 1,
    }))
  }

  const changes = diffLines(originalContent, currentContent)
  const alignedLines = []
  let leftLineNum = 1
  let rightLineNum = 1

  changes.forEach(change => {
    const lines = change.value.split('\n')
    if (lines[lines.length - 1] === '') lines.pop()

    if (change.removed) {
      lines.forEach(text => {
        alignedLines.push({
          type: 'delete',
          leftText: text,
          rightText: null,
          leftLineNum: leftLineNum++,
          rightLineNum: null,
        })
      })
    } else if (change.added) {
      lines.forEach(text => {
        alignedLines.push({
          type: 'insert',
          leftText: null,
          rightText: text,
          leftLineNum: null,
          rightLineNum: rightLineNum++,
        })
      })
    } else {
      lines.forEach(text => {
        alignedLines.push({
          type: 'normal',
          leftText: text,
          rightText: text,
          leftLineNum: leftLineNum++,
          rightLineNum: rightLineNum++,
        })
      })
    }
  })

  return alignedLines
}

// Editable cell component
function EditableCell({ text, lineNum, type, onChange, onKeyDown }) {
  const [localText, setLocalText] = useState(text)
  const spanRef = useRef(null)
  const isFocusedRef = useRef(false)

  useEffect(() => {
    // Only sync from parent when not actively editing
    if (!isFocusedRef.current) {
      setLocalText(text)
    }
  }, [text])

  const handleFocus = () => {
    isFocusedRef.current = true
  }

  const handleInput = (e) => {
    setLocalText(e.target.textContent)
  }

  const handleBlur = () => {
    isFocusedRef.current = false
    if (localText !== text) {
      onChange(lineNum, localText)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const selection = window.getSelection()
      const range = selection.getRangeAt(0)
      const cursorPos = range.startOffset
      onKeyDown(lineNum, 'split', cursorPos, localText)
    } else if (e.key === 'Backspace' && spanRef.current) {
      const selection = window.getSelection()
      const range = selection.getRangeAt(0)
      if (range.startOffset === 0 && range.endOffset === 0) {
        e.preventDefault()
        onKeyDown(lineNum, 'mergeUp', 0, localText)
      }
    }
  }

  const cellClass = type === 'insert'
    ? 'diff-cell diff-cell-right diff-cell-added'
    : 'diff-cell diff-cell-right'

  return (
    <div className={cellClass}>
      <span className="diff-line-num">{lineNum}</span>
      <span className="diff-line-marker">{type === 'insert' ? '+' : ''}</span>
      <span
        ref={spanRef}
        className="diff-line-text"
        contentEditable
        suppressContentEditableWarning
        onFocus={handleFocus}
        onInput={handleInput}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
      >
        {localText || '\u00A0'}
      </span>
    </div>
  )
}

// Single row containing both left and right cells
function DiffRow({ line, idx, onLineChange, onLineAction }) {
  // Left cell
  let leftCell
  if (line.type === 'insert') {
    // Spacer on left for insertion
    leftCell = (
      <div className="diff-cell diff-cell-left diff-cell-spacer">
        <span className="diff-line-num"></span>
        <span className="diff-line-marker"></span>
        <span className="diff-line-text">&nbsp;</span>
      </div>
    )
  } else if (line.type === 'delete') {
    leftCell = (
      <div className="diff-cell diff-cell-left diff-cell-deleted">
        <span className="diff-line-num">{line.leftLineNum}</span>
        <span className="diff-line-marker">-</span>
        <span className="diff-line-text">{line.leftText || '\u00A0'}</span>
      </div>
    )
  } else {
    leftCell = (
      <div className="diff-cell diff-cell-left">
        <span className="diff-line-num">{line.leftLineNum}</span>
        <span className="diff-line-marker"></span>
        <span className="diff-line-text">{line.leftText || '\u00A0'}</span>
      </div>
    )
  }

  // Right cell
  let rightCell
  if (line.type === 'delete') {
    // Spacer on right for deletion
    rightCell = (
      <div className="diff-cell diff-cell-right diff-cell-spacer">
        <span className="diff-line-num"></span>
        <span className="diff-line-marker"></span>
        <span className="diff-line-text">&nbsp;</span>
      </div>
    )
  } else {
    rightCell = (
      <EditableCell
        text={line.rightText || ''}
        lineNum={line.rightLineNum}
        type={line.type}
        onChange={onLineChange}
        onKeyDown={onLineAction}
      />
    )
  }

  return (
    <div className="diff-row" key={idx}>
      {leftCell}
      {rightCell}
    </div>
  )
}

export default function DiffHighlightPOC() {
  const originalContent = `# Hello World

This is the first paragraph.

This is the second paragraph that will be modified.

This is the third paragraph.

This line will be deleted.

The end.`

  const [currentContent, setCurrentContent] = useState(`# Hello World

This is the first paragraph.

This paragraph was MODIFIED with new content!

This is the third paragraph.

This is a completely NEW paragraph that was added!

The end.`)

  const [alignedLines, setAlignedLines] = useState([])
  const scrollRef = useRef(null)

  // Rebuild aligned lines when content changes
  useEffect(() => {
    const lines = buildAlignedLines(originalContent, currentContent)
    setAlignedLines(lines)
  }, [originalContent, currentContent])

  // Handle line content change
  const handleLineChange = useCallback((lineNum, newText) => {
    const lines = currentContent.split('\n')
    lines[lineNum - 1] = newText
    setCurrentContent(lines.join('\n'))
  }, [currentContent])

  // Handle line actions (split, merge)
  const handleLineAction = useCallback((lineNum, action, cursorPos, currentText) => {
    const lines = currentContent.split('\n')
    if (action === 'split') {
      const before = currentText.slice(0, cursorPos)
      const after = currentText.slice(cursorPos)
      lines[lineNum - 1] = before
      lines.splice(lineNum, 0, after)
      setCurrentContent(lines.join('\n'))
    } else if (action === 'mergeUp' && lineNum > 1) {
      const prevLine = lines[lineNum - 2]
      lines[lineNum - 2] = prevLine + currentText
      lines.splice(lineNum - 1, 1)
      setCurrentContent(lines.join('\n'))
    }
  }, [currentContent])

  return (
    <div className="diff-poc-container">
      <h2>Editable Diff View POC</h2>
      <p className="diff-poc-description">
        Left: Original (read-only) with deletions in red | Right: Editable with additions in green
      </p>

      <style>{`
        .diff-poc-container {
          padding: 20px;
          max-width: 1400px;
          margin: 0 auto;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .diff-poc-description {
          color: #666;
          margin-bottom: 20px;
        }
        .diff-split-view {
          border: 1px solid #d0d0d0;
          border-radius: 6px;
          overflow: auto;
          max-height: 500px;
          background: #1e1e1e;
        }

        .diff-table {
          width: 100%;
          font-family: 'SF Mono', Monaco, 'Courier New', monospace;
          font-size: 13px;
        }

        /* Row contains left and right cells side by side */
        .diff-row {
          display: flex;
          width: 100%;
        }

        /* Each cell is half width */
        .diff-cell {
          flex: 1;
          display: flex;
          min-height: ${LINE_HEIGHT}px;
          line-height: ${LINE_HEIGHT}px;
        }
        .diff-cell-left {
          border-right: 1px solid #3c3c3c;
        }

        .diff-line-num {
          width: 40px;
          padding: 0 8px;
          text-align: right;
          color: #6e7681;
          background: #161b22;
          flex-shrink: 0;
          user-select: none;
        }
        .diff-line-marker {
          width: 20px;
          text-align: center;
          flex-shrink: 0;
          color: #8b949e;
          user-select: none;
        }
        .diff-line-text {
          flex: 1;
          padding: 0 8px;
          white-space: pre-wrap;
          word-break: break-word;
          color: #c9d1d9;
          outline: none;
        }

        /* Deleted cells (left side - red) */
        .diff-cell-deleted {
          background-color: rgba(248, 81, 73, 0.15);
        }
        .diff-cell-deleted .diff-line-num {
          background-color: rgba(248, 81, 73, 0.2);
        }
        .diff-cell-deleted .diff-line-marker {
          color: #f85149;
        }
        .diff-cell-deleted .diff-line-text {
          color: #ffa198;
        }

        /* Added cells (right side - green) */
        .diff-cell-added {
          background-color: rgba(46, 160, 67, 0.15);
        }
        .diff-cell-added .diff-line-num {
          background-color: rgba(46, 160, 67, 0.2);
        }
        .diff-cell-added .diff-line-marker {
          color: #3fb950;
        }
        .diff-cell-added .diff-line-text {
          color: #7ee787;
        }

        /* Spacer cells (grey) */
        .diff-cell-spacer {
          background-color: rgba(110, 118, 129, 0.1);
        }
        .diff-cell-spacer .diff-line-num {
          background-color: rgba(110, 118, 129, 0.1);
        }
        .diff-cell-spacer .diff-line-text {
          color: transparent;
        }

        .diff-legend {
          margin-top: 20px;
          font-size: 12px;
          color: #666;
          display: flex;
          gap: 16px;
        }
        .diff-legend-item {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .diff-legend-color {
          width: 16px;
          height: 16px;
          border-radius: 3px;
        }
      `}</style>

      <div className="diff-split-view" ref={scrollRef}>
        <div className="diff-table">
          {alignedLines.map((line, idx) => (
            <DiffRow
              key={idx}
              line={line}
              idx={idx}
              onLineChange={handleLineChange}
              onLineAction={handleLineAction}
            />
          ))}
        </div>
      </div>

      <div className="diff-legend">
        <div className="diff-legend-item">
          <div className="diff-legend-color" style={{ background: 'rgba(248, 81, 73, 0.3)' }} />
          <span>Deleted</span>
        </div>
        <div className="diff-legend-item">
          <div className="diff-legend-color" style={{ background: 'rgba(46, 160, 67, 0.3)' }} />
          <span>Added</span>
        </div>
        <div className="diff-legend-item">
          <div className="diff-legend-color" style={{ background: 'rgba(110, 118, 129, 0.2)' }} />
          <span>Spacer</span>
        </div>
      </div>

      <div style={{ marginTop: '16px', padding: '12px', background: '#f6f8fa', borderRadius: '6px', fontSize: '12px' }}>
        <strong>Debug:</strong> {alignedLines.length} aligned lines |
        Original: {originalContent.split('\n').length} lines |
        Current: {currentContent.split('\n').length} lines
      </div>
    </div>
  )
}
