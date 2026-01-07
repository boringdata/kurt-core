import React, { useEffect, useMemo, useRef, useCallback, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import TextAlign from '@tiptap/extension-text-align'
import Highlight from '@tiptap/extension-highlight'
import { Markdown } from '@tiptap/markdown'
import { Extension } from '@tiptap/core'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { diffLines, diffWords } from 'diff'
import GitDiff from './GitDiff'
import FrontmatterEditor, { parseFrontmatter, reconstructContent } from './FrontmatterEditor'

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
// Compares: originalContent (git HEAD) vs editor.getMarkdown() (current editor state)
// Both go through Tiptap's markdown serializer for consistent comparison
function createDiffExtension(diffStateRef) {
  return Extension.create({
    name: 'diffDecorations',

    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey('diffDecorations'),
          props: {
            decorations(state) {
              // Check if diff mode is enabled
              const { enabled, originalContent, getEditorMarkdown } = diffStateRef.current || {}
              if (!enabled) {
                return DecorationSet.empty
              }

              const doc = state.doc

              // Get current editor content as markdown
              const currentMarkdown = getEditorMarkdown ? getEditorMarkdown() : ''

              // Compare: git HEAD vs current editor markdown
              const diffMap = buildDiffMap(originalContent || '', currentMarkdown)
              const { deletedLines, addedLineNumbers, wordDiffs } = diffMap

              const decorations = []

              // Build a mapping from markdown lines to document nodes
              // Each block node in Tiptap corresponds to one or more markdown lines
              const currentLines = currentMarkdown.split('\n')
              let mdLineIndex = 0 // Current position in markdown lines

              doc.descendants((node, nodePos) => {
                if (!node.isBlock) return false

                // Skip nodes that don't produce markdown content
                if (node.type.name === 'doc') return true

                // Each block node typically produces 1 markdown line
                // Lists are an exception but we handle them by iterating child nodes
                let linesForNode = 1

                // Try to match node content to markdown lines
                // Skip empty lines in markdown that might be separators
                while (mdLineIndex < currentLines.length && currentLines[mdLineIndex] === '') {
                  mdLineIndex++
                }

                // Check if any of the lines for this node are marked as changed
                let nodeIsChanged = false
                const nodeWordDiffs = []

                for (let i = 0; i < linesForNode && (mdLineIndex + i) < currentLines.length; i++) {
                  const lineNum = mdLineIndex + i + 1 // 1-indexed
                  if (addedLineNumbers.has(lineNum)) {
                    nodeIsChanged = true
                    const wd = wordDiffs.get(lineNum)
                    if (wd) nodeWordDiffs.push(...wd)
                  }
                }

                // Apply decorations
                if (nodeIsChanged) {
                  decorations.push(
                    Decoration.node(nodePos, nodePos + node.nodeSize, {
                      class: 'diff-line-added'
                    })
                  )

                  // Word-level highlights
                  if (nodeWordDiffs.length > 0 && node.isTextblock) {
                    let textOffset = 0
                    const textStart = nodePos + 1

                    nodeWordDiffs.forEach(part => {
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

                // Check for deleted lines before this node
                const lineNum = mdLineIndex + 1
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

                  // Copy button with icon
                  const copyBtn = document.createElement('button')
                  copyBtn.className = 'diff-copy-btn'
                  copyBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
                  copyBtn.title = 'Copy deleted text'
                  copyBtn.onclick = (e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    navigator.clipboard.writeText(deletedTexts.join('\n'))
                    copyBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>'
                    setTimeout(() => { copyBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>' }, 1500)
                  }
                  widget.appendChild(copyBtn)

                  decorations.push(
                    Decoration.widget(nodePos, widget, { side: -1 })
                  )
                }

                mdLineIndex += linesForNode
                return false
              })

              // Trailing deletions (at end of document)
              const lastLineNum = currentLines.length + 1
              const trailingDeleted = deletedLines.find(d => d.beforeLine >= lastLineNum)
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

  // Frontmatter state - separate from body content
  // Parse initial values from content prop
  const initialParsed = useMemo(() => parseFrontmatter(content || ''), [])
  const [frontmatterCollapsed, setFrontmatterCollapsed] = useState(
    !initialParsed.frontmatter || initialParsed.frontmatter.trim() === ''
  )
  const [currentFrontmatter, setCurrentFrontmatter] = useState(initialParsed.frontmatter)
  const [currentBody, setCurrentBody] = useState(initialParsed.body)
  const lastContentVersionRef = useRef(contentVersion)

  // Ref to access latest frontmatter in callbacks without stale closures
  const currentFrontmatterRef = useRef(initialParsed.frontmatter)
  currentFrontmatterRef.current = currentFrontmatter

  // Re-parse content only when contentVersion changes (external file reload)
  // NOT when content changes from typing (that would cause loops)
  useEffect(() => {
    // Skip if contentVersion hasn't changed
    if (contentVersion === lastContentVersionRef.current) return
    lastContentVersionRef.current = contentVersion

    const { frontmatter, body } = parseFrontmatter(content || '')
    setCurrentFrontmatter(frontmatter)
    setCurrentBody(body)
    // Auto-expand if there's frontmatter, collapse if not
    setFrontmatterCollapsed(!frontmatter || frontmatter.trim() === '')
  }, [content, contentVersion])

  // Base extensions used for both the editor and for normalizing original content
  // This ensures both sides go through the exact same Tiptap schema
  const baseExtensions = useMemo(
    () => [
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
      // Official Tiptap Markdown extension for bidirectional markdown support
      Markdown.configure({
        // Preserve line breaks as <br> tags
        markedOptions: {
          breaks: true,
          gfm: true,
        },
      }),
    ],
    []
  )

  // Create diff extension once, it uses the ref to check state
  const DiffExtension = useMemo(() => {
    return createDiffExtension(diffStateRef)
  }, [])

  // Handle frontmatter changes
  const handleFrontmatterChange = useCallback((newFrontmatter) => {
    setCurrentFrontmatter(newFrontmatter)
    const fullContent = reconstructContent(newFrontmatter, currentBody)

    if (onChange) {
      onChange(fullContent)
    }

    if (onAutoSave) {
      if (autoSaveTimer.current) {
        clearTimeout(autoSaveTimer.current)
      }
      autoSaveTimer.current = setTimeout(() => {
        const latestFullContent = reconstructContent(newFrontmatter, currentBody)
        onAutoSave(latestFullContent)
      }, autoSaveDelay)
    }
  }, [currentBody, onChange, onAutoSave, autoSaveDelay])

  const editor = useEditor({
    extensions: [...baseExtensions, DiffExtension],
    // Use contentType: 'markdown' to parse initial content as markdown
    // Start with body only (frontmatter handled separately)
    // Use initialParsed.body which is computed once on mount
    content: initialParsed.body || '',
    contentType: 'markdown',
    onUpdate: ({ editor: editorInstance }) => {
      // Use editor.getMarkdown() from @tiptap/markdown
      const bodyMarkdown = editorInstance.getMarkdown()
      setCurrentBody(bodyMarkdown)
      // Use ref to get latest frontmatter (avoids stale closure)
      const fullContent = reconstructContent(currentFrontmatterRef.current, bodyMarkdown)

      if (onChange) {
        onChange(fullContent)
      }

      if (onAutoSave) {
        if (autoSaveTimer.current) {
          clearTimeout(autoSaveTimer.current)
        }
        // Use a callback to get the latest content when the timer fires
        autoSaveTimer.current = setTimeout(() => {
          // Get fresh markdown at save time, not when update was triggered
          const latestBodyMarkdown = editorInstance.getMarkdown()
          const latestFullContent = reconstructContent(currentFrontmatterRef.current, latestBodyMarkdown)
          onAutoSave(latestFullContent)
        }, autoSaveDelay)
      }
    },
  })

  // Update diff state when mode or original content changes
  // For diff comparison, we use editor.getMarkdown() to get normalized output
  // This ensures both sides go through the same Tiptap markdown serializer
  useEffect(() => {
    const wasEnabled = diffStateRef.current.enabled
    const isEnabled = editorMode === 'diff' && originalContent !== null

    diffStateRef.current = {
      enabled: isEnabled,
      originalContent: originalContent,
      // getCurrentMarkdown will be called by the plugin to get fresh editor content
      getEditorMarkdown: () => editor?.getMarkdown() || '',
    }

    // Force editor to re-render decorations
    if (editor && (wasEnabled !== isEnabled || isEnabled)) {
      // Trigger a view update to recalculate decorations
      editor.view.dispatch(editor.state.tr)
    }
  }, [editorMode, originalContent, editor])

  // Only reset editor content when contentVersion changes (external file reload)
  // NOT when currentBody changes (which happens during typing/autosave)
  // Parse directly from content prop to avoid race conditions with state updates
  useEffect(() => {
    if (!editor) return
    if (contentVersion === undefined) return
    // Parse body directly from content prop (not state) to ensure we have latest value
    const { body } = parseFrontmatter(content || '')
    editor.commands.setContent(body || '', { contentType: 'markdown' })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentVersion, editor])

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

      {/* Frontmatter editor - only show in edit modes, not git-diff */}
      {editorMode !== 'git-diff' && (
        <FrontmatterEditor
          frontmatter={currentFrontmatter}
          onChange={handleFrontmatterChange}
          isCollapsed={frontmatterCollapsed}
          onToggleCollapse={() => setFrontmatterCollapsed(!frontmatterCollapsed)}
        />
      )}

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
