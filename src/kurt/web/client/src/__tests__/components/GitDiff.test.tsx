/**
 * Tests for GitDiff component
 *
 * Features tested:
 * - Diff parsing and rendering
 * - Split vs unified view types
 * - File headers
 * - Empty and invalid diff handling
 * - Multiple file diffs
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import GitDiff from '../../components/GitDiff'
import { diffs } from '../fixtures'

describe('GitDiff', () => {
  describe('Empty States', () => {
    it('shows message when diff is null', () => {
      render(<GitDiff diff={null} />)

      expect(screen.getByText('No git changes for this file.')).toBeInTheDocument()
    })

    it('shows message when diff is undefined', () => {
      render(<GitDiff diff={undefined} />)

      expect(screen.getByText('No git changes for this file.')).toBeInTheDocument()
    })

    it('shows message when diff is empty string', () => {
      render(<GitDiff diff="" />)

      expect(screen.getByText('No git changes for this file.')).toBeInTheDocument()
    })

    it('shows message when diff cannot be parsed', () => {
      render(<GitDiff diff={diffs.invalid} />)

      expect(screen.getByText('No changes to display.')).toBeInTheDocument()
    })
  })

  describe('Single File Diff', () => {
    it('renders diff content correctly', () => {
      render(<GitDiff diff={diffs.simple} />)

      // Should show the diff content
      expect(screen.getByText(/Hello/)).toBeInTheDocument()
    })

    it('shows file header by default', () => {
      render(<GitDiff diff={diffs.simple} />)

      expect(screen.getByText('b/src/App.jsx')).toBeInTheDocument()
    })

    it('hides file header when showFileHeader is false', () => {
      render(<GitDiff diff={diffs.simple} showFileHeader={false} />)

      expect(screen.queryByText('b/src/App.jsx')).not.toBeInTheDocument()
    })

    it('renders in split view by default', () => {
      const { container } = render(<GitDiff diff={diffs.simple} />)

      // react-diff-view uses specific classes for split view
      expect(container.querySelector('.diff-split')).toBeInTheDocument()
    })

    it('renders in unified view when specified', () => {
      const { container } = render(<GitDiff diff={diffs.simple} viewType="unified" />)

      expect(container.querySelector('.diff-unified')).toBeInTheDocument()
    })
  })

  describe('Multiple File Diffs', () => {
    it('renders all files in the diff', () => {
      render(<GitDiff diff={diffs.multipleFiles} />)

      expect(screen.getByText('b/file1.js')).toBeInTheDocument()
      expect(screen.getByText('b/file2.js')).toBeInTheDocument()
    })

    it('shows separate hunks for each file', () => {
      const { container } = render(<GitDiff diff={diffs.multipleFiles} />)

      const diffFiles = container.querySelectorAll('.diff-file')
      expect(diffFiles.length).toBe(2)
    })
  })

  describe('Diff Types', () => {
    it('handles deleted file diffs', () => {
      render(<GitDiff diff={diffs.deleted} />)

      // The diff should render without errors
      expect(screen.getByText(/deleted.js/)).toBeInTheDocument()
    })

    it('handles new file diffs', () => {
      render(<GitDiff diff={diffs.newFile} />)

      // The diff should render without errors
      expect(screen.getByText(/new.js/)).toBeInTheDocument()
    })
  })

  describe('Hunk Rendering', () => {
    it('renders added lines', () => {
      const { container } = render(<GitDiff diff={diffs.simple} />)

      // Added lines have specific classes in react-diff-view
      const addedLines = container.querySelectorAll('.diff-code-insert')
      expect(addedLines.length).toBeGreaterThan(0)
    })

    it('renders removed lines', () => {
      const { container } = render(<GitDiff diff={diffs.simple} />)

      // Removed lines have specific classes in react-diff-view
      const removedLines = container.querySelectorAll('.diff-code-delete')
      expect(removedLines.length).toBeGreaterThan(0)
    })

    it('renders context lines', () => {
      const { container } = render(<GitDiff diff={diffs.simple} />)

      // Context lines are present
      expect(container.querySelector('.diff')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has accessible diff container', () => {
      const { container } = render(<GitDiff diff={diffs.simple} />)

      expect(container.querySelector('.diff-content')).toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('applies diff-file class to each file section', () => {
      const { container } = render(<GitDiff diff={diffs.simple} />)

      expect(container.querySelector('.diff-file')).toBeInTheDocument()
    })

    it('applies diff-file-header class to file headers', () => {
      const { container } = render(<GitDiff diff={diffs.simple} />)

      expect(container.querySelector('.diff-file-header')).toBeInTheDocument()
    })
  })
})
