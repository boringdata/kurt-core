import { useMemo } from 'react'
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

  const lineCount = content.split('\n').length
  const gutterChars = Math.max(2, String(lineCount).length)

  return (
    <div className={`code-viewer ${className}`}>
      <style>{`
        .code-line::before {
          content: attr(data-line-number);
          display: inline-block;
          width: ${gutterChars}ch;
          margin-right: 1em;
          text-align: right;
          opacity: 0.5;
          user-select: none;
          pointer-events: none;
        }
      `}</style>
      <Highlight theme={themes.vsDark} code={content} language={language}>
        {({ className: highlightClass, style, tokens, getLineProps, getTokenProps }) => (
          <pre
            className={highlightClass}
            style={{
              ...style,
              margin: 0,
              padding: '1rem',
              overflow: 'auto',
              height: '100%',
              lineHeight: '1.5',
              tabSize: 4,
            }}
          >
            <code>
              {tokens.map((line, i) => {
                const lineProps = getLineProps({ line })
                const lineNum = String(i + 1).padStart(gutterChars, ' ')
                return (
                  <div
                    key={i}
                    {...lineProps}
                    className="code-line"
                    data-line-number={lineNum}
                  >
                    {line.map((token, key) => {
                      const tokenProps = getTokenProps({ token })
                      return <span key={key} {...tokenProps} />
                    })}
                  </div>
                )
              })}
            </code>
          </pre>
        )}
      </Highlight>
    </div>
  )
}
