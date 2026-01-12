/**
 * DiffEditor: Tiptap editor with inline diff highlighting
 * Shows deleted lines in red above modified content, added lines in green
 * Word-level highlighting for exact changes
 */
import { useEffect, useMemo, useRef } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
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
function createDiffExtension(originalContent) {
  return Extension.create({
    name: 'diffDecorations',

    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey('diffDecorations'),
          props: {
            decorations(state) {
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

              const diffMap = buildDiffMap(originalContent, currentContent)
              const { deletedLines, addedLineNumbers, wordDiffs } = diffMap

              // Debug: log what we're working with
              console.log('[DiffEditor] originalContent:', JSON.stringify(originalContent?.slice(0, 100)))
              console.log('[DiffEditor] currentContent:', JSON.stringify(currentContent?.slice(0, 100)))
              console.log('[DiffEditor] addedLineNumbers:', [...addedLineNumbers])

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

export default function DiffEditor({
  content,
  originalContent,
  contentVersion,
  onChange,
  onAutoSave,
  autoSaveDelay = 800,
}) {
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

  // Extract plain text from original for comparison
  // We need to render it through Tiptap the same way current content is rendered,
  // then extract text the same way we do in the plugin
  const originalPlainText = useMemo(() => {
    if (!originalContent) return ''
    // Parse markdown to HTML, then extract text content line by line
    // This matches how we extract from the Tiptap doc in the plugin
    const html = markdownParser.render(originalContent)
    // Create a temporary div to parse the HTML
    const div = document.createElement('div')
    div.innerHTML = html
    // Extract text from block elements (p, h1, h2, etc.)
    const lines = []
    div.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li').forEach(el => {
      lines.push(el.textContent || '')
    })
    return lines.join('\n')
  }, [originalContent, markdownParser])

  // Create diff extension with original content
  const DiffExtension = useMemo(() => {
    return createDiffExtension(originalPlainText)
  }, [originalPlainText])

  const autoSaveTimerRef = useRef(null)

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: { class: 'editor-link' },
      }),
      Placeholder.configure({
        placeholder: 'Start writing...',
      }),
      TaskList,
      TaskItem.configure({ nested: true }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
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
        if (autoSaveTimerRef.current) {
          clearTimeout(autoSaveTimerRef.current)
        }
        autoSaveTimerRef.current = setTimeout(() => {
          onAutoSave(markdown)
        }, autoSaveDelay)
      }
    },
  }, [DiffExtension])

  // Update content when contentVersion changes
  useEffect(() => {
    if (!editor) return
    if (contentVersion === undefined) return
    const html = content ? markdownParser.render(content) : ''
    editor.commands.setContent(html)
  }, [contentVersion, editor, content, markdownParser])

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
      }
    }
  }, [autoSaveTimerRef])

  return (
    <div className="diff-editor-wrapper">
      <EditorContent editor={editor} />
    </div>
  )
}
