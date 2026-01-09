import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react'
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
              <svg className="save-spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" />
              </svg>
            </span>
          ) : isDirty ? (
            <span className="save-status-dirty" title="Unsaved changes">
              <span className="save-dot" />
            </span>
          ) : (
            <span className="save-status-saved" title="Saved">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12" />
              </svg>
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
            fontFamily: "'IBM Plex Mono', Monaco, 'Courier New', monospace",
            fontSize: 13,
            lineHeight: 1.5,
            backgroundColor: '#1e1e1e',
            color: '#d4d4d4',
            minHeight: '100%',
          }}
        />
      </div>
    </div>
  )
}
