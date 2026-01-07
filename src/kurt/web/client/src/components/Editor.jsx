import React, { useEffect, useMemo, useRef, useCallback } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import TextAlign from '@tiptap/extension-text-align'
import Highlight from '@tiptap/extension-highlight'
import { Extension } from '@tiptap/core'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { diffLines, diffWords } from 'diff'
import MarkdownIt from 'markdown-it'
import TurndownService from 'turndown'
import { gfm } from 'turndown-plugin-gfm'
import GitDiff from './GitDiff'

// Build a map of line changes with word-level diff info
function buildDiffMap(originalContent, currentContent) {
  // If content is identical, no changes
  if (originalContent === currentContent) {
    return { deletedLines: [], addedLineNumbers: new Set(), wordDiffs: new Map() }
  }

  // If no original content (new file), mark ALL lines as added
  if (!originalContent) {
    const lines = currentContent ? currentContent.split('\n') : []
    const addedLineNumbers = new Set()
    for (let i = 1; i <= lines.length; i++) {
      addedLineNumbers.add(i)
    }
    return { deletedLines: [], addedLineNumbers, wordDiffs: new Map() }
  }

  const changes = diffLines(originalContent, currentContent)
  const deletedLines = []
  const addedLineNumbers = new Set()
  const wordDiffs = new Map()

  let originalLineNum = 0
  let currentLineNum = 0
  let pendingDeleted = []
  let pendingDeletedTexts = []

  changes.forEach(change => {
    const lines = change.value.split('\n')
    if (lines[lines.length - 1] === '') lines.pop()

    if (change.removed) {
      lines.forEach(text => {
        pendingDeleted.push(text)
        pendingDeletedTexts.push(text)
        originalLineNum++
      })
    } else if (change.added) {
      lines.forEach((text, idx) => {
        currentLineNum++
        addedLineNumbers.add(currentLineNum)

        if (idx < pendingDeletedTexts.length) {
          const oldText = pendingDeletedTexts[idx]
          const wordChanges = diffWords(oldText, text)
          wordDiffs.set(currentLineNum, wordChanges)
        }

        if (idx === 0 && pendingDeleted.length > 0) {
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
// Uses a ref to access the current diff state reactively
function createDiffExtension(diffStateRef, markdownParser) {
  return Extension.create({
    name: 'diffDecorations',

    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey('diffDecorations'),
          props: {
            decorations(state) {
              // Check if diff mode is enabled
              const { enabled, originalContent } = diffStateRef.current || {}
              if (!enabled) {
                return DecorationSet.empty
              }

              const doc = state.doc

              // Extract text content from document for comparison
              let currentLines = []
              doc.descendants((node) => {
                if (node.isBlock && node.isTextblock) {
                  currentLines.push(node.textContent)
                }
                return false
              })
              const currentContent = currentLines.join('\n')

              // Convert original markdown to plain text the same way
              let originalPlainText = ''
              if (originalContent) {
                const html = markdownParser.render(originalContent)
                const div = document.createElement('div')
                div.innerHTML = html
                const lines = []
                div.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li').forEach(el => {
                  lines.push(el.textContent || '')
                })
                originalPlainText = lines.join('\n')
              }

              const diffMap = buildDiffMap(originalPlainText, currentContent)
              const { deletedLines, addedLineNumbers, wordDiffs } = diffMap

              const decorations = []
              let lineNum = 0

              doc.descendants((node, nodePos) => {
                if (node.isBlock) {
                  lineNum++

                  // Green background for added/modified lines
                  if (addedLineNumbers.has(lineNum)) {
                    decorations.push(
                      Decoration.node(nodePos, nodePos + node.nodeSize, {
                        class: 'diff-line-added'
                      })
                    )

                    // Word-level highlights
                    const lineWordDiffs = wordDiffs.get(lineNum)
                    if (lineWordDiffs && node.isTextblock) {
                      let textOffset = 0
                      const textStart = nodePos + 1

                      lineWordDiffs.forEach(part => {
                        if (part.added) {
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
                          textOffset += part.value.length
                        }
                      })
                    }
                  }

                  // Deleted lines widget
                  const deletedBefore = deletedLines.find(d => d.beforeLine === lineNum)
                  if (deletedBefore) {
                    const widget = document.createElement('div')
                    widget.className = 'diff-deleted-block'
                    widget.contentEditable = 'false'

                    const deletedTexts = []

                    if (deletedBefore.wordDiffs) {
                      deletedBefore.wordDiffs.forEach(({ text, wordChanges }) => {
                        const lineDiv = document.createElement('div')
                        lineDiv.className = 'diff-deleted-line'
                        deletedTexts.push(text)

                        if (wordChanges) {
                          wordChanges.forEach(part => {
                            const span = document.createElement('span')
                            if (part.removed) {
                              span.className = 'diff-word-removed'
                              span.textContent = part.value
                              lineDiv.appendChild(span)
                            } else if (!part.added) {
                              span.textContent = part.value
                              lineDiv.appendChild(span)
                            }
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

                    // Copy button
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
                return false
              })

              // Trailing deletions
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

function MenuBar({ editor }) {
  const setLink = useCallback(() => {
    if (!editor) return
    const previousUrl = editor.getAttributes('link').href
    const url = window.prompt('URL', previousUrl)
    if (url === null) return
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
  }, [editor])

  if (!editor) return null

  return (
    <div className="editor-menu">
      <div className="menu-group">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={editor.isActive('bold') ? 'is-active' : ''}
          title="Bold (Ctrl+B)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/>
            <path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/>
          </svg>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={editor.isActive('italic') ? 'is-active' : ''}
          title="Italic (Ctrl+I)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="19" y1="4" x2="10" y2="4"/>
            <line x1="14" y1="20" x2="5" y2="20"/>
            <line x1="15" y1="4" x2="9" y2="20"/>
          </svg>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          className={editor.isActive('underline') ? 'is-active' : ''}
          title="Underline (Ctrl+U)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M6 3v7a6 6 0 0 0 6 6 6 6 0 0 0 6-6V3"/>
            <line x1="4" y1="21" x2="20" y2="21"/>
          </svg>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleStrike().run()}
          className={editor.isActive('strike') ? 'is-active' : ''}
          title="Strikethrough"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="4" y1="12" x2="20" y2="12"/>
            <path d="M17.5 7.5c-.6-1.4-2.2-2.5-4.5-2.5-3 0-5 1.5-5 4 0 1.8 1 3 4 3.5"/>
            <path d="M10 16.5c0 1.5 1.5 2.5 4 2.5 2.5 0 4-1.2 4-3"/>
          </svg>
        </button>
      </div>

      <div className="menu-separator" />

      <div className="menu-group">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          className={editor.isActive('heading', { level: 1 }) ? 'is-active' : ''}
          title="Heading 1"
        >
          <span className="text-btn">H1</span>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={editor.isActive('heading', { level: 2 }) ? 'is-active' : ''}
          title="Heading 2"
        >
          <span className="text-btn">H2</span>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          className={editor.isActive('heading', { level: 3 }) ? 'is-active' : ''}
          title="Heading 3"
        >
          <span className="text-btn">H3</span>
        </button>
      </div>

      <div className="menu-separator" />

      <div className="menu-group">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={editor.isActive('bulletList') ? 'is-active' : ''}
          title="Bullet List"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="9" y1="6" x2="20" y2="6"/>
            <line x1="9" y1="12" x2="20" y2="12"/>
            <line x1="9" y1="18" x2="20" y2="18"/>
            <circle cx="4" cy="6" r="1.5" fill="currentColor"/>
            <circle cx="4" cy="12" r="1.5" fill="currentColor"/>
            <circle cx="4" cy="18" r="1.5" fill="currentColor"/>
          </svg>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={editor.isActive('orderedList') ? 'is-active' : ''}
          title="Numbered List"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="10" y1="6" x2="21" y2="6"/>
            <line x1="10" y1="12" x2="21" y2="12"/>
            <line x1="10" y1="18" x2="21" y2="18"/>
            <text x="3" y="8" fontSize="7" fill="currentColor" stroke="none">1</text>
            <text x="3" y="14" fontSize="7" fill="currentColor" stroke="none">2</text>
            <text x="3" y="20" fontSize="7" fill="currentColor" stroke="none">3</text>
          </svg>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleTaskList().run()}
          className={editor.isActive('taskList') ? 'is-active' : ''}
          title="Task List"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="5" width="6" height="6" rx="1"/>
            <path d="M5 8l1.5 1.5 3-3"/>
            <line x1="12" y1="8" x2="21" y2="8"/>
            <rect x="3" y="13" width="6" height="6" rx="1"/>
            <line x1="12" y1="16" x2="21" y2="16"/>
          </svg>
        </button>
      </div>

      <div className="menu-separator" />

      <div className="menu-group">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          className={editor.isActive('blockquote') ? 'is-active' : ''}
          title="Quote"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 17h3l2-4V7H5v6h3l-2 4zm8 0h3l2-4V7h-6v6h3l-2 4z"/>
          </svg>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          className={editor.isActive('codeBlock') ? 'is-active' : ''}
          title="Code Block"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="16 18 22 12 16 6"/>
            <polyline points="8 6 2 12 8 18"/>
          </svg>
        </button>
        <button
          type="button"
          onClick={setLink}
          className={editor.isActive('link') ? 'is-active' : ''}
          title="Add Link"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
          </svg>
        </button>
        <button
          type="button"
          onClick={() => editor.chain().focus().setHorizontalRule().run()}
          title="Horizontal Rule"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="12" x2="21" y2="12"/>
          </svg>
        </button>
      </div>

      <div className="menu-separator" />

      <div className="menu-group">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHighlight().run()}
          className={editor.isActive('highlight') ? 'is-active' : ''}
          title="Highlight"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 20h9"/>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
          </svg>
        </button>
      </div>
    </div>
  )
}

function SaveStatus({ isDirty, isSaving }) {
  if (isSaving) {
    return (
      <div className="save-status save-status-saving" title="Saving...">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" strokeDasharray="31.4" strokeDashoffset="10">
            <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite"/>
          </circle>
        </svg>
      </div>
    )
  }

  if (isDirty) {
    return (
      <div className="save-status save-status-dirty" title="Unsaved changes">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="12" r="5"/>
        </svg>
      </div>
    )
  }

  return (
    <div className="save-status save-status-saved" title="All changes saved">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="20 6 9 17 4 12" />
      </svg>
    </div>
  )
}

// Editor modes: 'rendered' (default Tiptap), 'diff' (inline diff editing), 'git-diff' (legacy read-only diff)
export default function Editor({
  content,
  contentVersion,
  isDirty,
  isSaving,
  onChange,
  onAutoSave,
  autoSaveDelay = 800,
  showDiffToggle = false,
  diffText = '',
  diffError = '',
  // Props for inline diff mode
  editorMode = 'rendered', // 'rendered' | 'diff' | 'git-diff'
  originalContent = null,
  onModeChange,
}) {
  const autoSaveTimer = useRef(null)
  const diffStateRef = useRef({ enabled: false, originalContent: null })

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
    const service = new TurndownService({
      codeBlockStyle: 'fenced',
      headingStyle: 'atx',
      bulletListMarker: '-',
    })
    service.use(gfm)
    return service
  }, [])

  // Create diff extension once, it uses the ref to check state
  const DiffExtension = useMemo(() => {
    return createDiffExtension(diffStateRef, markdownParser)
  }, [markdownParser])

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'editor-link',
        },
      }),
      Placeholder.configure({
        placeholder: 'Start writing...',
      }),
      TaskList,
      TaskItem.configure({
        nested: true,
      }),
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      Highlight,
      DiffExtension,
    ],
    content: content ? markdownParser.render(content) : '',
    onUpdate: ({ editor }) => {
      const html = editor.getHTML()
      const markdown = turndown.turndown(html)
      if (onChange) {
        onChange(markdown)
      }

      if (onAutoSave) {
        if (autoSaveTimer.current) {
          clearTimeout(autoSaveTimer.current)
        }
        autoSaveTimer.current = setTimeout(() => {
          onAutoSave(markdown)
        }, autoSaveDelay)
      }
    },
  })

  // Update diff state when mode or original content changes
  useEffect(() => {
    const wasEnabled = diffStateRef.current.enabled
    diffStateRef.current = {
      enabled: editorMode === 'diff' && originalContent !== null,
      originalContent: originalContent,
    }
    // Force editor to re-render decorations
    if (editor && (wasEnabled !== diffStateRef.current.enabled || diffStateRef.current.enabled)) {
      // Trigger a view update to recalculate decorations
      editor.view.dispatch(editor.state.tr)
    }
  }, [editorMode, originalContent, editor])

  useEffect(() => {
    if (!editor) return
    if (contentVersion === undefined) return
    const html = content ? markdownParser.render(content) : ''
    editor.commands.setContent(html)
  }, [contentVersion, editor, content])

  useEffect(() => {
    return () => {
      if (autoSaveTimer.current) {
        clearTimeout(autoSaveTimer.current)
      }
    }
  }, [])

  const handleDrop = useCallback((event) => {
    const fileData = event.dataTransfer.getData('application/x-kurt-file')
    if (fileData && editor) {
      event.preventDefault()
      try {
        const file = JSON.parse(fileData)
        if (file.path) {
          const linkText = file.name || file.path.split('/').pop()
          editor.chain().focus().insertContent(`[${linkText}](${file.path})`).run()
        }
      } catch (e) {
        // Ignore parse errors
      }
    }
  }, [editor])

  const handleDragOver = useCallback((event) => {
    if (event.dataTransfer.types.includes('application/x-kurt-file')) {
      event.preventDefault()
      event.stopPropagation()
    }
  }, [])

  // Mode selector for when diff is available
  const renderModeSelector = () => {
    if (!showDiffToggle) return null

    return (
      <div className="editor-mode-selector">
        <button
          type="button"
          className={`mode-btn${editorMode === 'rendered' ? ' active' : ''}`}
          onClick={() => onModeChange?.('rendered')}
          title="Edit rendered content"
        >
          Edit
        </button>
        <button
          type="button"
          className={`mode-btn${editorMode === 'diff' ? ' active' : ''}`}
          onClick={() => onModeChange?.('diff')}
          title="Edit with inline diff highlighting"
        >
          Diff
        </button>
        <button
          type="button"
          className={`mode-btn${editorMode === 'git-diff' ? ' active' : ''}`}
          onClick={() => onModeChange?.('git-diff')}
          title="View git diff (read-only)"
        >
          Raw
        </button>
      </div>
    )
  }

  // Render the appropriate content based on mode
  const renderContent = () => {
    if (editorMode === 'git-diff') {
      return (
        <>
          {diffError && <div className="diff-error">{diffError}</div>}
          <GitDiff diff={diffText} showFileHeader={false} />
        </>
      )
    }

    // Both 'rendered' and 'diff' modes use the same editor
    // The diff decorations are applied via the plugin when in diff mode
    if (editorMode === 'diff' && diffError) {
      return <div className="diff-error">{diffError}</div>
    }
    if (editorMode === 'diff' && originalContent === null) {
      return <div className="diff-loading">Loading original content...</div>
    }

    return <EditorContent editor={editor} />
  }

  return (
    <div className="editor-wrapper">
      <div className="editor-toolbar">
        <MenuBar editor={editor} />
        <div className="editor-toolbar-right">
          {editorMode !== 'git-diff' && <SaveStatus isDirty={isDirty} isSaving={isSaving} />}
          {renderModeSelector()}
        </div>
      </div>
      <div
        className="editor-content"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        {renderContent()}
      </div>
    </div>
  )
}
