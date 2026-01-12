/**
 * POC: Tiptap editor with deleted lines shown in red above modified lines
 * Uses Tiptap decorations to inject read-only deleted content
 */
import { useState, useEffect, useMemo } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Extension } from '@tiptap/core'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { diffLines, diffWords } from 'diff'
import MarkdownIt from 'markdown-it'
import TurndownService from 'turndown'

// Build a map of line changes with word-level diff info
function buildDiffMap(originalContent, currentContent) {
  if (originalContent === currentContent) {
    return { deletedLines: [], addedLineNumbers: new Set(), wordDiffs: new Map() }
  }

  const changes = diffLines(originalContent, currentContent)
  const deletedLines = [] // { beforeLine: number, texts: string[], wordDiffs: array }
  const addedLineNumbers = new Set()
  const wordDiffs = new Map() // lineNum -> array of {text, added, removed}

  let originalLineNum = 0
  let currentLineNum = 0
  let pendingDeleted = []
  let pendingDeletedTexts = []

  changes.forEach(change => {
    const lines = change.value.split('\n')
    if (lines[lines.length - 1] === '') lines.pop()

    if (change.removed) {
      // Collect deleted lines
      lines.forEach(text => {
        pendingDeleted.push(text)
        pendingDeletedTexts.push(text)
        originalLineNum++
      })
    } else if (change.added) {
      // Mark added lines and compute word-level diffs with pending deletions
      lines.forEach((text, idx) => {
        currentLineNum++
        addedLineNumbers.add(currentLineNum)

        // Compute word-level diff if we have a corresponding deleted line
        if (idx < pendingDeletedTexts.length) {
          const oldText = pendingDeletedTexts[idx]
          const wordChanges = diffWords(oldText, text)
          wordDiffs.set(currentLineNum, wordChanges)
        }

        if (idx === 0 && pendingDeleted.length > 0) {
          // Compute word diffs for deleted lines too
          const deletedWithWordDiffs = pendingDeleted.map((delText, delIdx) => {
            if (delIdx < lines.length) {
              return {
                text: delText,
                wordChanges: diffWords(delText, lines[delIdx])
              }
            }
            return { text: delText, wordChanges: null }
          })

          deletedLines.push({
            beforeLine: currentLineNum,
            texts: pendingDeleted,
            wordDiffs: deletedWithWordDiffs
          })
          pendingDeleted = []
          pendingDeletedTexts = []
        }
      })
    } else {
      // Unchanged lines
      if (pendingDeleted.length > 0) {
        deletedLines.push({
          beforeLine: currentLineNum + 1,
          texts: [...pendingDeleted],
          wordDiffs: pendingDeleted.map(t => ({ text: t, wordChanges: null }))
        })
        pendingDeleted = []
        pendingDeletedTexts = []
      }
      lines.forEach(() => {
        originalLineNum++
        currentLineNum++
      })
    }
  })

  // Handle trailing deletions
  if (pendingDeleted.length > 0) {
    deletedLines.push({
      beforeLine: currentLineNum + 1,
      texts: [...pendingDeleted],
      wordDiffs: pendingDeleted.map(t => ({ text: t, wordChanges: null }))
    })
  }

  return { deletedLines, addedLineNumbers, wordDiffs }
}

// Create Tiptap extension for diff decorations
// originalContent is passed in and diff is computed on every doc change
function createDiffExtension(originalContent, turndown) {
  return Extension.create({
    name: 'diffDecorations',

    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey('diffDecorations'),
          props: {
            decorations(state) {
              const doc = state.doc

              // Get current content as markdown from the document
              // We need to extract text content to compare with original
              let currentLines = []
              doc.descendants((node) => {
                if (node.isBlock && node.isTextblock) {
                  currentLines.push(node.textContent)
                }
                return false
              })
              const currentContent = currentLines.join('\n')

              // Build diff map
              const diffMap = buildDiffMap(originalContent, currentContent)
              const { deletedLines, addedLineNumbers, wordDiffs } = diffMap

              const decorations = []
              let lineNum = 0

              doc.descendants((node, nodePos) => {
                if (node.isBlock) {
                  lineNum++

                  // Add green background for added lines
                  if (addedLineNumbers.has(lineNum)) {
                    decorations.push(
                      Decoration.node(nodePos, nodePos + node.nodeSize, {
                        class: 'diff-line-added'
                      })
                    )

                    // Add word-level highlights for changed words
                    const lineWordDiffs = wordDiffs.get(lineNum)
                    if (lineWordDiffs && node.isTextblock) {
                      let textOffset = 0
                      const textStart = nodePos + 1 // +1 to skip the opening tag

                      lineWordDiffs.forEach(part => {
                        if (part.added) {
                          // Highlight added words
                          const from = textStart + textOffset
                          const to = from + part.value.length
                          if (to <= nodePos + node.nodeSize - 1) {
                            decorations.push(
                              Decoration.inline(from, to, {
                                class: 'diff-word-added'
                              })
                            )
                          }
                          textOffset += part.value.length
                        } else if (!part.removed) {
                          // Unchanged text - just advance offset
                          textOffset += part.value.length
                        }
                        // Skip removed parts - they don't exist in current text
                      })
                    }
                  }

                  // Add deleted lines widget before this line
                  const deletedBefore = deletedLines.find(d => d.beforeLine === lineNum)
                  if (deletedBefore) {
                    const widget = document.createElement('div')
                    widget.className = 'diff-deleted-block'
                    widget.contentEditable = 'false' // Prevent cursor from entering

                    // Collect text for copy button
                    const deletedTexts = []

                    // Use wordDiffs if available for word-level highlighting
                    if (deletedBefore.wordDiffs) {
                      deletedBefore.wordDiffs.forEach(({ text, wordChanges }) => {
                        const lineDiv = document.createElement('div')
                        lineDiv.className = 'diff-deleted-line'
                        deletedTexts.push(text)

                        if (wordChanges) {
                          // Render with word-level highlighting
                          wordChanges.forEach(part => {
                            const span = document.createElement('span')
                            if (part.removed) {
                              span.className = 'diff-word-removed'
                              span.textContent = part.value
                              lineDiv.appendChild(span)
                            } else if (!part.added) {
                              // Unchanged text
                              span.textContent = part.value
                              lineDiv.appendChild(span)
                            }
                            // Skip added parts in deleted line view
                          })
                        } else {
                          lineDiv.textContent = text || '\u00A0'
                        }

                        widget.appendChild(lineDiv)
                      })
                    } else {
                      deletedBefore.texts.forEach(text => {
                        const lineDiv = document.createElement('div')
                        lineDiv.className = 'diff-deleted-line'
                        lineDiv.textContent = text || '\u00A0'
                        deletedTexts.push(text)
                        widget.appendChild(lineDiv)
                      })
                    }

                    // Add copy button with mouseenter/mouseleave for better hover handling
                    const copyBtn = document.createElement('button')
                    copyBtn.className = 'diff-copy-btn'
                    copyBtn.textContent = '📋'
                    copyBtn.title = 'Copy deleted text'
                    copyBtn.onclick = (e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      navigator.clipboard.writeText(deletedTexts.join('\n'))
                      copyBtn.textContent = '✓'
                      setTimeout(() => { copyBtn.textContent = '📋' }, 1500)
                    }
                    // Show/hide on widget hover (backup for CSS hover)
                    widget.addEventListener('mouseenter', () => {
                      copyBtn.style.opacity = '1'
                    })
                    widget.addEventListener('mouseleave', () => {
                      copyBtn.style.opacity = '0.3'
                    })
                    widget.appendChild(copyBtn)

                    decorations.push(
                      Decoration.widget(nodePos, widget, { side: -1 })
                    )
                  }
                }
                return false // Don't descend into children
              })

              // Handle deletions at the very end
              const trailingDeleted = deletedLines.find(d => d.beforeLine === lineNum + 1)
              if (trailingDeleted) {
                const widget = document.createElement('div')
                widget.className = 'diff-deleted-block'
                trailingDeleted.texts.forEach(text => {
                  const lineDiv = document.createElement('div')
                  lineDiv.className = 'diff-deleted-line'
                  lineDiv.textContent = text || '\u00A0'
                  widget.appendChild(lineDiv)
                })
                decorations.push(
                  Decoration.widget(doc.content.size, widget, { side: 1 })
                )
              }

              return DecorationSet.create(doc, decorations)
            }
          }
        })
      ]
    }
  })
}

export default function TiptapDiffPOC() {
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

  // Markdown parser and turndown for converting to/from HTML
  const markdownParser = useMemo(
    () =>
      new MarkdownIt({
        html: false,
        linkify: true,
        breaks: true,
      }),
    [],
  )

  const turndown = useMemo(() => {
    return new TurndownService({
      codeBlockStyle: 'fenced',
      headingStyle: 'atx',
      bulletListMarker: '-',
    })
  }, [])

  // For comparison, extract just text content from original (strip markdown)
  const originalPlainText = useMemo(() => {
    return originalContent
      .split('\n')
      .map(line => line.replace(/^#+\s*/, '').trim()) // Remove heading markers
      .filter(line => line.length > 0)
      .join('\n')
  }, [originalContent])

  // Create extension once with original content - it will compute diff on each render
  const DiffExtension = useMemo(() => {
    return createDiffExtension(originalPlainText, turndown)
  }, [originalPlainText, turndown])

  // For debug display
  const diffMap = useMemo(() => {
    return buildDiffMap(originalContent, currentContent)
  }, [originalContent, currentContent])

  const editor = useEditor({
    extensions: [
      StarterKit,
      DiffExtension,
    ],
    content: markdownParser.render(currentContent),
    onUpdate: ({ editor }) => {
      const html = editor.getHTML()
      const markdown = turndown.turndown(html)
      setCurrentContent(markdown)
    },
  }, [DiffExtension])

  // Update editor content when diffMap changes (but not from typing)
  useEffect(() => {
    if (editor && !editor.isFocused) {
      const html = editor.getHTML()
      const currentMarkdown = turndown.turndown(html)
      if (currentMarkdown !== currentContent) {
        editor.commands.setContent(markdownParser.render(currentContent))
      }
    }
  }, [editor, currentContent, markdownParser, turndown])

  return (
    <div className="tiptap-diff-poc">
      <h2>Tiptap Diff POC</h2>
      <p className="poc-description">
        Deleted lines shown in red above modified content. Green background for additions.
      </p>

      <style>{`
        .tiptap-diff-poc {
          padding: 20px;
          max-width: 900px;
          margin: 0 auto;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .poc-description {
          color: #666;
          margin-bottom: 20px;
        }
        .tiptap-editor-container {
          border: 1px solid #d0d0d0;
          border-radius: 6px;
          background: #1e1e1e;
          padding: 16px;
          min-height: 400px;
        }
        .tiptap-editor-container .ProseMirror {
          outline: none;
          font-family: 'SF Mono', Monaco, 'Courier New', monospace;
          font-size: 14px;
          line-height: 1.6;
          color: #c9d1d9;
        }
        .tiptap-editor-container .ProseMirror p {
          margin: 0;
          padding: 4px 8px;
        }
        .tiptap-editor-container .ProseMirror h1,
        .tiptap-editor-container .ProseMirror h2,
        .tiptap-editor-container .ProseMirror h3 {
          margin: 0;
          padding: 4px 8px;
          color: #c9d1d9;
        }

        /* Added line - green background */
        .diff-line-added {
          background-color: rgba(46, 160, 67, 0.15) !important;
          border-left: 3px solid #3fb950;
        }
        .diff-line-added p,
        .diff-line-added h1,
        .diff-line-added h2 {
          color: #7ee787 !important;
        }

        /* Deleted lines block - red */
        .diff-deleted-block {
          background-color: rgba(248, 81, 73, 0.15);
          border-left: 3px solid #f85149;
          margin: 0;
          padding: 0;
          position: relative;
        }
        .diff-copy-btn {
          position: absolute;
          right: 8px;
          top: 4px;
          padding: 4px 8px;
          font-size: 14px;
          background: rgba(248, 81, 73, 0.3);
          border: 1px solid #f85149;
          border-radius: 4px;
          color: #ffa198;
          cursor: pointer;
          opacity: 0.3;
          transition: opacity 0.15s, background 0.15s;
          z-index: 10;
        }
        .diff-copy-btn:hover {
          background: rgba(248, 81, 73, 0.6);
          opacity: 1 !important;
        }
        .diff-deleted-line {
          padding: 4px 8px;
          font-family: 'SF Mono', Monaco, 'Courier New', monospace;
          font-size: 14px;
          line-height: 1.6;
          color: #ffa198;
          opacity: 0.9;
        }
        /* Word-level highlight for removed text */
        .diff-word-removed {
          background-color: rgba(248, 81, 73, 0.4);
          text-decoration: line-through;
          border-radius: 2px;
          padding: 1px 2px;
        }
        /* Word-level highlight for added text */
        .diff-word-added {
          background-color: rgba(46, 160, 67, 0.4);
          border-radius: 2px;
          padding: 1px 2px;
        }

        .debug-info {
          margin-top: 16px;
          padding: 12px;
          background: #f6f8fa;
          border-radius: 6px;
          font-size: 12px;
        }
      `}</style>

      <div className="tiptap-editor-container">
        <EditorContent editor={editor} />
      </div>

      <div className="debug-info">
        <strong>Debug:</strong> {diffMap.deletedLines.length} deleted blocks |
        {diffMap.addedLineNumbers.size} added lines |
        Original: {originalContent.split('\n').length} lines |
        Current: {currentContent.split('\n').length} lines
      </div>
    </div>
  )
}
