/**
 * File tree and file content fixtures for testing
 */

export interface FileEntry {
  name: string
  path: string
  is_dir: boolean
}

export interface GitStatus {
  [path: string]: 'M' | 'A' | 'D' | 'U'
}

// File tree entry factory
export const createFileEntry = (overrides: Partial<FileEntry> = {}): FileEntry => ({
  name: 'file.md',
  path: 'file.md',
  is_dir: false,
  ...overrides,
})

// Pre-built file tree fixtures
export const fileTree = {
  root: [
    createFileEntry({ name: 'README.md', path: 'README.md' }),
    createFileEntry({ name: 'package.json', path: 'package.json' }),
    createFileEntry({ name: 'src', path: 'src', is_dir: true }),
    createFileEntry({ name: 'docs', path: 'docs', is_dir: true }),
  ],

  srcDir: [
    createFileEntry({ name: 'index.js', path: 'src/index.js' }),
    createFileEntry({ name: 'App.jsx', path: 'src/App.jsx' }),
    createFileEntry({ name: 'components', path: 'src/components', is_dir: true }),
    createFileEntry({ name: 'utils', path: 'src/utils', is_dir: true }),
  ],

  componentsDir: [
    createFileEntry({ name: 'Button.jsx', path: 'src/components/Button.jsx' }),
    createFileEntry({ name: 'Modal.jsx', path: 'src/components/Modal.jsx' }),
  ],

  docsDir: [
    createFileEntry({ name: 'getting-started.md', path: 'docs/getting-started.md' }),
    createFileEntry({ name: 'api.md', path: 'docs/api.md' }),
  ],

  empty: [],
}

// Git status fixtures
export const gitStatus = {
  clean: {},

  withChanges: {
    'src/App.jsx': 'M' as const,
    'docs/api.md': 'M' as const,
    'src/components/Button.jsx': 'A' as const,
    'old-file.js': 'D' as const,
    'new-feature.js': 'U' as const,
  },

  allModified: {
    'file1.js': 'M' as const,
    'file2.js': 'M' as const,
    'file3.js': 'M' as const,
  },

  allNew: {
    'new1.js': 'U' as const,
    'new2.js': 'U' as const,
  },
}

// Search result fixtures
export const searchResults = {
  empty: { results: [] },

  basic: {
    results: [
      { name: 'App.jsx', path: 'src/App.jsx', dir: 'src' },
      { name: 'App.test.jsx', path: 'src/__tests__/App.test.jsx', dir: 'src/__tests__' },
    ],
  },

  multiple: {
    results: [
      { name: 'index.js', path: 'src/index.js', dir: 'src' },
      { name: 'index.html', path: 'public/index.html', dir: 'public' },
      { name: 'index.css', path: 'src/index.css', dir: 'src' },
    ],
  },
}

// File content fixtures
export const fileContents = {
  markdown: {
    simple: '# Hello World\n\nThis is a simple markdown file.',

    withFrontmatter: `---
title: My Document
date: 2024-01-15
tags: [test, example]
---

# My Document

This is the content.`,

    complex: `---
title: Complex Document
author: Test Author
date: 2024-01-15
category: tutorial
tags:
  - react
  - testing
  - vitest
published: true
---

# Complex Document

## Introduction

This is a complex markdown document with various elements.

### Features

- **Bold text** and *italic text*
- [Links](https://example.com)
- Code blocks

\`\`\`javascript
const hello = 'world';
console.log(hello);
\`\`\`

### Task List

- [x] Completed task
- [ ] Pending task
- [ ] Another pending task

> This is a blockquote

| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |
`,
  },

  code: {
    javascript: `import React from 'react';

function Component({ name }) {
  return <div>Hello, {name}!</div>;
}

export default Component;`,

    python: `def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello("World"))`,

    json: `{
  "name": "test-package",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0"
  }
}`,
  },

  empty: '',
}

// Frontmatter fixtures
export const frontmatter = {
  empty: '',

  simple: `title: My Document
date: 2024-01-15`,

  complex: `title: Complex Document
author: Test Author
date: 2024-01-15
category: tutorial
tags:
  - react
  - testing
  - vitest
published: true`,

  invalid: `title: Invalid YAML
  bad indentation: true
	tabs: not allowed`,
}

// Diff fixtures
export const diffs = {
  simple: `diff --git a/src/App.jsx b/src/App.jsx
index 1234567..abcdefg 100644
--- a/src/App.jsx
+++ b/src/App.jsx
@@ -1,5 +1,6 @@
 import React from 'react';

 function App() {
-  return <div>Hello</div>;
+  const name = "World";
+  return <div>Hello, {name}!</div>;
 }`,

  multipleFiles: `diff --git a/file1.js b/file1.js
index 1234567..abcdefg 100644
--- a/file1.js
+++ b/file1.js
@@ -1,3 +1,4 @@
+// Added comment
 const a = 1;
 const b = 2;
 const c = 3;
diff --git a/file2.js b/file2.js
index 1234567..abcdefg 100644
--- a/file2.js
+++ b/file2.js
@@ -1,3 +1,3 @@
 const x = 1;
-const y = 2;
+const y = 3;
 const z = 3;`,

  deleted: `diff --git a/deleted.js b/deleted.js
deleted file mode 100644
index 1234567..0000000
--- a/deleted.js
+++ /dev/null
@@ -1,3 +0,0 @@
-const a = 1;
-const b = 2;
-const c = 3;`,

  newFile: `diff --git a/new.js b/new.js
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/new.js
@@ -0,0 +1,3 @@
+const a = 1;
+const b = 2;
+const c = 3;`,

  empty: '',
  invalid: 'not a valid diff format',
}

// Helper to create a deep file tree
export const createDeepTree = (depth: number, filesPerLevel: number = 2): FileEntry[] => {
  const entries: FileEntry[] = []
  const createLevel = (parentPath: string, currentDepth: number) => {
    if (currentDepth >= depth) return

    for (let i = 0; i < filesPerLevel; i++) {
      const name = `file${i}.js`
      const path = parentPath ? `${parentPath}/${name}` : name
      entries.push(createFileEntry({ name, path, is_dir: false }))
    }

    const dirName = `dir${currentDepth}`
    const dirPath = parentPath ? `${parentPath}/${dirName}` : dirName
    entries.push(createFileEntry({ name: dirName, path: dirPath, is_dir: true }))
    createLevel(dirPath, currentDepth + 1)
  }

  createLevel('', 0)
  return entries
}
