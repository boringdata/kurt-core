import React, { useEffect, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'

export default function Editor({ content, onSave }) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: content || '<p></p>',
  })

  useEffect(() => {
    if (editor && content !== undefined) {
      editor.commands.setContent(content)
    }
  }, [content, editor])

  const handleSave = () => {
    if (!editor) return
    const html = editor.getHTML()
    onSave(html)
  }

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <button onClick={handleSave}>Save</button>
      </div>
      <div>
        <EditorContent editor={editor} />
      </div>
    </div>
  )
}
