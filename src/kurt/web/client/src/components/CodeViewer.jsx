import React, { useMemo } from 'react'
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

export default function CodeViewer({ content, filename, className = '' }) {
  const language = useMemo(() => getLanguage(filename), [filename])

  if (!content) {
    return (
      <div className={`code-viewer code-viewer-empty ${className}`}>
        <span className="code-empty-message">No content</span>
      </div>
    )
  }

  return (
    <div className={`code-viewer ${className}`}>
      <Highlight theme={themes.vsDark} code={content} language={language}>
        {({ className: highlightClass, style, tokens, getLineProps, getTokenProps }) => (
          <pre className={highlightClass} style={{ ...style, margin: 0, padding: '1rem', overflow: 'auto', height: '100%' }}>
            {tokens.map((line, i) => (
              <div key={i} {...getLineProps({ line })} style={{ display: 'table-row' }}>
                <span
                  className="code-line-number"
                  style={{
                    display: 'table-cell',
                    textAlign: 'right',
                    paddingRight: '1rem',
                    userSelect: 'none',
                    opacity: 0.5,
                    width: '1%',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {i + 1}
                </span>
                <span style={{ display: 'table-cell' }}>
                  {line.map((token, key) => (
                    <span key={key} {...getTokenProps({ token })} />
                  ))}
                </span>
              </div>
            ))}
          </pre>
        )}
      </Highlight>
    </div>
  )
}
