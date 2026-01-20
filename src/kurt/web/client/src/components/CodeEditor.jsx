import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { Loader2, Check } from 'lucide-react'
import Editor from 'react-simple-code-editor'
import { Highlight, themes } from 'prism-react-renderer'

// Map file extensions to Prism language names
const getLanguage = (filename) => {
  if (!filename) return 'text'
  const ext = filename.split('.').pop()?.toLowerCase()

  const languageMap = {
    js: 'javascript',
    jsx: 'jsx',
    ts: 'typescript',
    tsx: 'tsx',
    py: 'python',
    rb: 'ruby',
    rs: 'rust',
    go: 'go',
    java: 'java',
    c: 'c',
    cpp: 'cpp',
    h: 'c',
    hpp: 'cpp',
    cs: 'csharp',
    php: 'php',
    swift: 'swift',
    kt: 'kotlin',
    scala: 'scala',
    sh: 'bash',
    bash: 'bash',
    zsh: 'bash',
    fish: 'bash',
    ps1: 'powershell',
    sql: 'sql',
    graphql: 'graphql',
    gql: 'graphql',
    json: 'json',
    yaml: 'yaml',
    yml: 'yaml',
    toml: 'toml',
    xml: 'markup',
    html: 'markup',
    htm: 'markup',
    svg: 'markup',
    css: 'css',
    scss: 'scss',
    sass: 'sass',
    less: 'less',
    dockerfile: 'docker',
    makefile: 'makefile',
    cmake: 'cmake',
    diff: 'diff',
    patch: 'diff',
    gitignore: 'git',
    env: 'bash',
    ini: 'ini',
    conf: 'ini',
    cfg: 'ini',
  }

  return languageMap[ext] || 'text'
}

export default function CodeEditor({
  content,
  contentVersion,
  filename,
  isDirty,
  isSaving,
  onChange,
  onAutoSave,
  className = '',
}) {
  const language = useMemo(() => getLanguage(filename), [filename])
  const [localContent, setLocalContent] = useState(content || '')
  const autoSaveTimerRef = useRef(null)

  // Sync local content when external content changes
  useEffect(() => {
    setLocalContent(content || '')
  }, [content, contentVersion])

  const handleChange = useCallback(
    (newContent) => {
      setLocalContent(newContent)
      onChange?.(newContent)

      // Debounced auto-save
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
      }
      autoSaveTimerRef.current = setTimeout(() => {
        onAutoSave?.(newContent)
      }, 1000)
    },
    [onChange, onAutoSave]
  )

  // Cleanup auto-save timer
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current)
      }
    }
  }, [])

  // Highlight function for prism-react-renderer with line numbers
  const highlightCode = useCallback(
    (code) => (
      <Highlight theme={themes.vsDark} code={code} language={language}>
        {({ tokens, getLineProps, getTokenProps }) => (
          <>
            {tokens.map((line, i) => (
              <div key={i} {...getLineProps({ line })} style={{ display: 'table-row' }}>
                <span className="code-editor-line-number">{i + 1}</span>
                <span style={{ display: 'table-cell' }}>
                  {line.map((token, key) => (
                    <span key={key} {...getTokenProps({ token })} />
                  ))}
                </span>
              </div>
            ))}
          </>
        )}
      </Highlight>
    ),
    [language]
  )

  return (
    <div className={`code-editor ${className}`}>
      <div className="code-editor-toolbar">
        <span className="code-editor-language">{language}</span>
        <div className="code-editor-status">
          {isSaving ? (
            <span className="save-status-saving">
              <Loader2 className="save-spinner" size={14} />
            </span>
          ) : isDirty ? (
            <span className="save-status-dirty" title="Unsaved changes">
              <span className="save-dot" />
            </span>
          ) : (
            <span className="save-status-saved" title="Saved">
              <Check size={14} />
            </span>
          )}
        </div>
      </div>

      <div className="code-editor-container">
        <Editor
          value={localContent}
          onValueChange={handleChange}
          highlight={highlightCode}
          padding={16}
          className="code-editor-input"
          textareaClassName="code-editor-textarea"
          preClassName="code-editor-pre"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 13,
            lineHeight: 1.5,
            backgroundColor: 'var(--color-pre-bg)',
            color: 'var(--color-pre-text)',
            minHeight: '100%',
          }}
        />
      </div>
    </div>
  )
}
