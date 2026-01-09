import React from 'react'
import { Diff, Hunk, parseDiff } from 'react-diff-view'
import 'react-diff-view/style/index.css'

export default function GitDiff({ diff, showFileHeader = true, viewType = 'split' }) {
  if (!diff) {
    return <div className="diff-empty">No git changes for this file.</div>
  }

  let files = []
  try {
    files = parseDiff(diff)
  } catch (error) {
    return <div className="diff-empty">Unable to parse diff.</div>
  }
  if (!files.length) {
    return <div className="diff-empty">No changes to display.</div>
  }

  return (
    <div className="diff-content">
      {files.map((file) => (
        <div key={`${file.oldPath}-${file.newPath}`} className="diff-file">
          {showFileHeader && <div className="diff-file-header">{file.newPath}</div>}
          <Diff viewType={viewType} diffType={file.type} hunks={file.hunks}>
            {(hunks) => hunks.map((hunk) => <Hunk key={hunk.content} hunk={hunk} />)}
          </Diff>
        </div>
      ))}
    </div>
  )
}
