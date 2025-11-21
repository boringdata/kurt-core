import React, { useEffect, useState } from 'react'

export default function FileTree({ onOpen }) {
  const [entries, setEntries] = useState([])

  useEffect(() => {
    fetch('/api/tree')
      .then((r) => r.json())
      .then((data) => setEntries(data.entries || []))
      .catch(() => setEntries([]))
  }, [])

  return (
    <div>
      <h3>Project</h3>
      <div>
        {entries.map((e) => (
          <div key={e.path} className="file-item" onClick={() => onOpen(e.path)}>
            {e.is_dir ? '📁' : '📄'} {e.name}
          </div>
        ))}
      </div>
    </div>
  )
}
