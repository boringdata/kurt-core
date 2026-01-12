/**
 * Tests for FrontmatterEditor component
 *
 * Features tested:
 * - YAML syntax highlighting
 * - Collapse/expand behavior
 * - Diff mode (side-by-side view)
 * - YAML validation
 * - Debounced onChange
 * - Badges (Changed, Invalid)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import FrontmatterEditor, { parseFrontmatter, reconstructContent } from '../../components/FrontmatterEditor'
import { frontmatter } from '../fixtures'

describe('FrontmatterEditor', () => {
  const defaultProps = {
    frontmatter: frontmatter.simple,
    onChange: vi.fn(),
    isCollapsed: false,
    onToggleCollapse: vi.fn(),
    isDiffMode: false,
    originalFrontmatter: null,
  }

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  describe('parseFrontmatter utility', () => {
    it('returns empty frontmatter for content without frontmatter', () => {
      const result = parseFrontmatter('# Just a heading\n\nSome content')
      expect(result.frontmatter).toBe('')
      expect(result.body).toBe('# Just a heading\n\nSome content')
    })

    it('parses frontmatter correctly', () => {
      const content = `---
title: Test
date: 2024-01-15
---

# Heading`
      const result = parseFrontmatter(content)
      expect(result.frontmatter).toBe('title: Test\ndate: 2024-01-15')
      expect(result.body).toBe('\n# Heading')
    })

    it('handles empty content', () => {
      const result = parseFrontmatter('')
      expect(result.frontmatter).toBe('')
      expect(result.body).toBe('')
    })

    it('handles null/undefined content', () => {
      const result = parseFrontmatter(null as unknown as string)
      expect(result.frontmatter).toBe('')
      expect(result.body).toBe('')
    })

    it('handles Windows-style line endings', () => {
      const content = '---\r\ntitle: Test\r\n---\r\n\r\nContent'
      const result = parseFrontmatter(content)
      expect(result.frontmatter).toBe('title: Test')
    })
  })

  describe('reconstructContent utility', () => {
    it('returns body only when frontmatter is empty', () => {
      const result = reconstructContent('', '# Heading\n\nContent')
      expect(result).toBe('# Heading\n\nContent')
    })

    it('reconstructs full content with frontmatter', () => {
      const result = reconstructContent('title: Test', '# Heading')
      expect(result).toBe('---\ntitle: Test\n---\n# Heading')
    })

    it('handles whitespace-only frontmatter', () => {
      const result = reconstructContent('   ', '# Heading')
      expect(result).toBe('# Heading')
    })
  })

  describe('Rendering', () => {
    it('renders with header and toggle button', () => {
      render(<FrontmatterEditor {...defaultProps} />)

      expect(screen.getByText('Metadata')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /collapse|expand/i })).toBeInTheDocument()
    })

    it('shows YAML badge when frontmatter has content', () => {
      render(<FrontmatterEditor {...defaultProps} />)

      expect(screen.getByText('YAML')).toBeInTheDocument()
    })

    it('hides YAML badge when frontmatter is empty', () => {
      render(<FrontmatterEditor {...defaultProps} frontmatter="" />)

      expect(screen.queryByText('YAML')).not.toBeInTheDocument()
    })

    it('shows placeholder when frontmatter is empty and expanded', () => {
      render(<FrontmatterEditor {...defaultProps} frontmatter="" />)

      expect(screen.getByText(/title: My Document/)).toBeInTheDocument()
    })

    it('shows hint when frontmatter is empty', () => {
      render(<FrontmatterEditor {...defaultProps} frontmatter="" />)

      expect(screen.getByText('Add title, date, tags...')).toBeInTheDocument()
    })
  })

  describe('Collapse/Expand', () => {
    it('calls onToggleCollapse when header is clicked', () => {
      render(<FrontmatterEditor {...defaultProps} />)

      fireEvent.click(screen.getByText('Metadata'))
      expect(defaultProps.onToggleCollapse).toHaveBeenCalled()
    })

    it('hides content when collapsed', () => {
      render(<FrontmatterEditor {...defaultProps} isCollapsed={true} />)

      expect(screen.queryByText(/title:/)).not.toBeInTheDocument()
    })

    it('shows content when expanded', () => {
      render(<FrontmatterEditor {...defaultProps} isCollapsed={false} />)

      // The editor textarea should contain the frontmatter
      const textarea = document.querySelector('.frontmatter-textarea')
      expect(textarea).toBeInTheDocument()
    })

    it('rotates toggle icon when collapsed', () => {
      const { rerender } = render(<FrontmatterEditor {...defaultProps} isCollapsed={false} />)

      const expandedSvg = document.querySelector('.frontmatter-toggle svg')
      expect(expandedSvg).toHaveStyle({ transform: 'rotate(0deg)' })

      rerender(<FrontmatterEditor {...defaultProps} isCollapsed={true} />)

      const collapsedSvg = document.querySelector('.frontmatter-toggle svg')
      expect(collapsedSvg).toHaveStyle({ transform: 'rotate(-90deg)' })
    })
  })

  describe('Editing', () => {
    it('updates internal value when editing', async () => {
      render(<FrontmatterEditor {...defaultProps} />)

      const textarea = document.querySelector('.frontmatter-textarea') as HTMLTextAreaElement
      fireEvent.change(textarea, { target: { value: 'title: Updated' } })

      // Value updates synchronously
      expect(textarea.value).toBe('title: Updated')
    })

    it('debounces onChange callback', async () => {
      render(<FrontmatterEditor {...defaultProps} />)

      const textarea = document.querySelector('.frontmatter-textarea') as HTMLTextAreaElement
      fireEvent.change(textarea, { target: { value: 'title: Change 1' } })
      fireEvent.change(textarea, { target: { value: 'title: Change 2' } })
      fireEvent.change(textarea, { target: { value: 'title: Change 3' } })

      // onChange should not have been called yet
      expect(defaultProps.onChange).not.toHaveBeenCalled()

      // Advance timers past debounce
      await vi.advanceTimersByTimeAsync(350)

      // Should only be called once with final value
      expect(defaultProps.onChange).toHaveBeenCalledTimes(1)
      expect(defaultProps.onChange).toHaveBeenCalledWith('title: Change 3')
    })

    it('syncs with external frontmatter changes', () => {
      const { rerender } = render(<FrontmatterEditor {...defaultProps} frontmatter="title: Original" />)

      rerender(<FrontmatterEditor {...defaultProps} frontmatter="title: Updated externally" />)

      const textarea = document.querySelector('.frontmatter-textarea') as HTMLTextAreaElement
      expect(textarea.value).toBe('title: Updated externally')
    })
  })

  describe('YAML Validation', () => {
    it('shows Invalid badge when YAML contains tabs', async () => {
      render(<FrontmatterEditor {...defaultProps} />)

      const textarea = document.querySelector('.frontmatter-textarea') as HTMLTextAreaElement
      fireEvent.change(textarea, { target: { value: 'title:\tBadYaml' } })

      // Advance timers to trigger debounced validation
      await vi.advanceTimersByTimeAsync(350)

      // Check for the Invalid badge by class
      const badge = document.querySelector('.frontmatter-error-badge')
      expect(badge).toBeInTheDocument()
    })

    it('applies error class when YAML is invalid', async () => {
      render(<FrontmatterEditor {...defaultProps} />)

      const textarea = document.querySelector('.frontmatter-textarea') as HTMLTextAreaElement
      fireEvent.change(textarea, { target: { value: 'title:\tBadYaml' } })

      // Advance timers to trigger debounced validation
      await vi.advanceTimersByTimeAsync(350)

      const editor = document.querySelector('.frontmatter-editor')
      expect(editor).toHaveClass('has-error')
    })

    it('removes error state when YAML is fixed', async () => {
      render(<FrontmatterEditor {...defaultProps} />)

      const textarea = document.querySelector('.frontmatter-textarea') as HTMLTextAreaElement

      // First make it invalid
      fireEvent.change(textarea, { target: { value: 'title:\tBadYaml' } })
      await vi.advanceTimersByTimeAsync(350)
      const invalidBadge = document.querySelector('.frontmatter-error-badge')
      expect(invalidBadge).toBeInTheDocument()

      // Then fix it
      fireEvent.change(textarea, { target: { value: 'title: Valid' } })
      await vi.advanceTimersByTimeAsync(350)

      const noBadge = document.querySelector('.frontmatter-error-badge')
      expect(noBadge).not.toBeInTheDocument()
    })

    it('allows empty frontmatter without error', () => {
      render(<FrontmatterEditor {...defaultProps} frontmatter="" />)

      const editor = document.querySelector('.frontmatter-editor')
      expect(editor).not.toHaveClass('has-error')
    })
  })

  describe('Diff Mode', () => {
    it('shows side-by-side view in diff mode', () => {
      render(
        <FrontmatterEditor
          {...defaultProps}
          isDiffMode={true}
          originalFrontmatter="title: OldValue"
          frontmatter="title: NewValue"
        />
      )

      // Use getAllByText since labels may appear multiple times in the DOM
      const originalLabels = screen.getAllByText('Original')
      const currentLabels = screen.getAllByText(/Current/)
      expect(originalLabels.length).toBeGreaterThan(0)
      expect(currentLabels.length).toBeGreaterThan(0)
    })

    it('shows Changed badge when frontmatter differs from original', () => {
      render(
        <FrontmatterEditor
          {...defaultProps}
          isDiffMode={true}
          originalFrontmatter="title: Original"
          frontmatter="title: Modified"
        />
      )

      expect(screen.getByText('Changed')).toBeInTheDocument()
    })

    it('does not show Changed badge when frontmatter matches original', () => {
      render(
        <FrontmatterEditor
          {...defaultProps}
          isDiffMode={true}
          originalFrontmatter="title: Same"
          frontmatter="title: Same"
        />
      )

      expect(screen.queryByText('Changed')).not.toBeInTheDocument()
    })

    it('shows "No metadata" message when original is empty', () => {
      render(
        <FrontmatterEditor
          {...defaultProps}
          isDiffMode={true}
          originalFrontmatter=""
          frontmatter="title: New"
        />
      )

      expect(screen.getByText('No metadata')).toBeInTheDocument()
    })

    it('shows (modified) label on current side when changed', () => {
      render(
        <FrontmatterEditor
          {...defaultProps}
          isDiffMode={true}
          originalFrontmatter="title: Original"
          frontmatter="title: Modified"
        />
      )

      expect(screen.getByText(/Current.*\(modified\)/)).toBeInTheDocument()
    })

    it('displays original frontmatter as read-only', () => {
      render(
        <FrontmatterEditor
          {...defaultProps}
          isDiffMode={true}
          originalFrontmatter="title: Original"
          frontmatter="title: Modified"
        />
      )

      // Original side should be a pre element, not editable
      const originalSide = document.querySelector('.frontmatter-diff-original')
      expect(originalSide?.querySelector('pre')).toBeInTheDocument()
      expect(originalSide?.querySelector('textarea')).not.toBeInTheDocument()
    })

    it('allows editing in current side during diff mode', () => {
      render(
        <FrontmatterEditor
          {...defaultProps}
          isDiffMode={true}
          originalFrontmatter="title: Original"
          frontmatter="title: Modified"
        />
      )

      const currentSide = document.querySelector('.frontmatter-diff-current')
      expect(currentSide?.querySelector('textarea')).toBeInTheDocument()
    })
  })

  describe('Syntax Highlighting', () => {
    it('renders with Prism syntax highlighting', () => {
      render(<FrontmatterEditor {...defaultProps} frontmatter={frontmatter.complex} />)

      // Prism adds token classes for syntax highlighting
      expect(document.querySelector('.token')).toBeInTheDocument()
    })

    it('shows line numbers', () => {
      render(<FrontmatterEditor {...defaultProps} frontmatter={frontmatter.complex} />)

      const lineNumbers = document.querySelectorAll('.frontmatter-line-number')
      expect(lineNumbers.length).toBeGreaterThan(0)
    })
  })

  describe('Cleanup', () => {
    it('clears debounce timeout on unmount', () => {
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout')

      const { unmount } = render(<FrontmatterEditor {...defaultProps} />)

      const textarea = document.querySelector('.frontmatter-textarea') as HTMLTextAreaElement
      fireEvent.change(textarea, { target: { value: 'title: Test' } })

      unmount()

      expect(clearTimeoutSpy).toHaveBeenCalled()
    })
  })
})
