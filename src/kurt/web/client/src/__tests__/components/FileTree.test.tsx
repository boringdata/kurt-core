/**
 * Tests for FileTree component
 *
 * Features tested:
 * - Directory expand/collapse
 * - File selection and active state
 * - Search functionality
 * - Git status badges
 * - Context menu operations
 * - Drag and drop
 * - File creation/rename/delete
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import FileTree from '../../components/FileTree'
import { fileTree, gitStatus, searchResults } from '../fixtures'
import { setupApiMocks, flushPromises, simulateContextMenu, simulateDragDrop } from '../utils'

describe('FileTree', () => {
  const defaultProps = {
    onOpen: vi.fn(),
    onOpenToSide: vi.fn(),
    onFileDeleted: vi.fn(),
    onFileRenamed: vi.fn(),
    onFileMoved: vi.fn(),
    projectRoot: '/project',
    activeFile: null,
    creatingFile: false,
    onFileCreated: vi.fn(),
    onCancelCreate: vi.fn(),
  }

  beforeEach(() => {
    vi.useFakeTimers()
    setupApiMocks({
      '/api/tree': { entries: fileTree.root },
      '/api/git/status': { available: true, files: gitStatus.clean },
      '/api/search': searchResults.empty,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders file tree with root entries', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText('README.md')).toBeInTheDocument()
        expect(screen.getByText('package.json')).toBeInTheDocument()
        expect(screen.getByText('src')).toBeInTheDocument()
        expect(screen.getByText('docs')).toBeInTheDocument()
      })
    })

    it('shows search input', () => {
      render(<FileTree {...defaultProps} />)

      expect(screen.getByPlaceholderText('Search files...')).toBeInTheDocument()
    })

    it('shows project title', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      expect(screen.getByText('Project')).toBeInTheDocument()
    })

    it('retries fetch if initial load returns empty', async () => {
      const fetchMock = vi.fn()
        .mockResolvedValueOnce({ json: () => Promise.resolve({ entries: [] }) })
        .mockResolvedValueOnce({ json: () => Promise.resolve({ entries: [] }) })
        .mockResolvedValue({ json: () => Promise.resolve({ entries: fileTree.root }) })

      vi.stubGlobal('fetch', fetchMock)

      render(<FileTree {...defaultProps} />)

      // Wait for retries
      await vi.advanceTimersByTimeAsync(1000)

      await waitFor(() => {
        expect(screen.getByText('README.md')).toBeInTheDocument()
      })
    })
  })

  describe('Directory Expand/Collapse', () => {
    it('expands directory on click', async () => {
      setupApiMocks({
        '/api/tree?path=.': { entries: fileTree.root },
        '/api/tree?path=src': { entries: fileTree.srcDir },
        '/api/git/status': { available: true, files: {} },
      })

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      fireEvent.click(screen.getByText('src'))

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText('index.js')).toBeInTheDocument()
        expect(screen.getByText('App.jsx')).toBeInTheDocument()
      })
    })

    it('collapses expanded directory on click', async () => {
      setupApiMocks({
        '/api/tree?path=.': { entries: fileTree.root },
        '/api/tree?path=src': { entries: fileTree.srcDir },
        '/api/git/status': { available: true, files: {} },
      })

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      // Expand
      fireEvent.click(screen.getByText('src'))
      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText('index.js')).toBeInTheDocument()
      })

      // Collapse
      fireEvent.click(screen.getByText('src'))

      await waitFor(() => {
        expect(screen.queryByText('index.js')).not.toBeInTheDocument()
      })
    })

    it('shows folder icon for collapsed directories', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      // Collapsed folder icon
      expect(screen.getByText('📁')).toBeInTheDocument()
    })

    it('shows open folder icon for expanded directories', async () => {
      setupApiMocks({
        '/api/tree?path=.': { entries: fileTree.root },
        '/api/tree?path=src': { entries: fileTree.srcDir },
        '/api/git/status': { available: true, files: {} },
      })

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      fireEvent.click(screen.getByText('src'))

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText('📂')).toBeInTheDocument()
      })
    })
  })

  describe('File Selection', () => {
    it('calls onOpen when file is clicked', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      fireEvent.click(screen.getByText('README.md'))

      expect(defaultProps.onOpen).toHaveBeenCalledWith('README.md')
    })

    it('highlights active file', async () => {
      render(<FileTree {...defaultProps} activeFile="README.md" />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')
      expect(fileItem).toHaveClass('file-item-active')
    })

    it('does not call onOpen when directory is clicked', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      fireEvent.click(screen.getByText('src'))

      expect(defaultProps.onOpen).not.toHaveBeenCalled()
    })
  })

  describe('Search', () => {
    it('shows search results when typing', async () => {
      setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: {} },
        '/api/search': searchResults.basic,
      })

      render(<FileTree {...defaultProps} />)

      const searchInput = screen.getByPlaceholderText('Search files...')
      fireEvent.change(searchInput, { target: { value: 'App' } })

      await vi.advanceTimersByTimeAsync(250)

      await waitFor(() => {
        expect(screen.getByText('App.jsx')).toBeInTheDocument()
      })
    })

    it('shows "Searching..." while searching', async () => {
      render(<FileTree {...defaultProps} />)

      const searchInput = screen.getByPlaceholderText('Search files...')
      fireEvent.change(searchInput, { target: { value: 'test' } })

      expect(screen.getByText('Searching...')).toBeInTheDocument()
    })

    it('shows "No files found" for empty results', async () => {
      setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: {} },
        '/api/search': { results: [] },
      })

      render(<FileTree {...defaultProps} />)

      const searchInput = screen.getByPlaceholderText('Search files...')
      fireEvent.change(searchInput, { target: { value: 'nonexistent' } })

      await vi.advanceTimersByTimeAsync(250)

      await waitFor(() => {
        expect(screen.getByText('No files found')).toBeInTheDocument()
      })
    })

    it('highlights matching text in search results', async () => {
      setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: {} },
        '/api/search': searchResults.basic,
      })

      render(<FileTree {...defaultProps} />)

      const searchInput = screen.getByPlaceholderText('Search files...')
      fireEvent.change(searchInput, { target: { value: 'App' } })

      await vi.advanceTimersByTimeAsync(250)

      await waitFor(() => {
        expect(screen.getByRole('mark')).toBeInTheDocument()
      })
    })

    it('clears search when clear button is clicked', async () => {
      render(<FileTree {...defaultProps} />)

      const searchInput = screen.getByPlaceholderText('Search files...')
      fireEvent.change(searchInput, { target: { value: 'test' } })

      const clearButton = screen.getByRole('button')
      fireEvent.click(clearButton)

      expect(searchInput).toHaveValue('')
    })

    it('opens file when search result is clicked', async () => {
      setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: {} },
        '/api/search': searchResults.basic,
      })

      render(<FileTree {...defaultProps} />)

      const searchInput = screen.getByPlaceholderText('Search files...')
      fireEvent.change(searchInput, { target: { value: 'App' } })

      await vi.advanceTimersByTimeAsync(250)

      await waitFor(() => {
        fireEvent.click(screen.getByText('App.jsx'))
      })

      expect(defaultProps.onOpen).toHaveBeenCalledWith('src/App.jsx')
    })
  })

  describe('Git Status', () => {
    it('shows modified badge for modified files', async () => {
      setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: { 'README.md': 'M' } },
      })

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText('M')).toBeInTheDocument()
      })
    })

    it('shows new badge for untracked files', async () => {
      setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: { 'README.md': 'U' } },
      })

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByText('N')).toBeInTheDocument()
      })
    })

    it('shows dot indicator on directory with changed files', async () => {
      setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: { 'src/App.jsx': 'M' } },
      })

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        const srcDir = screen.getByText('src').closest('.file-item')
        expect(srcDir?.querySelector('.dir-changes-dot')).toBeInTheDocument()
      })
    })

    it('polls for git status periodically', async () => {
      const fetchMock = setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: {} },
      })

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      // Initial fetch
      expect(fetchMock).toHaveBeenCalled()
      const initialCalls = fetchMock.mock.calls.length

      // Wait for polling interval (5000ms)
      await vi.advanceTimersByTimeAsync(5500)

      // Should have more calls after polling
      expect(fetchMock.mock.calls.length).toBeGreaterThan(initialCalls)
    })
  })

  describe('Context Menu', () => {
    it('shows context menu on right-click', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')!
      fireEvent.contextMenu(fileItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        expect(screen.getByText('Rename')).toBeInTheDocument()
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })
    })

    it('shows "Open to the Side" for files', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')!
      fireEvent.contextMenu(fileItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        expect(screen.getByText('Open to the Side')).toBeInTheDocument()
      })
    })

    it('does not show "Open to the Side" for directories', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const dirItem = screen.getByText('src').closest('.file-item')!
      fireEvent.contextMenu(dirItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        expect(screen.queryByText('Open to the Side')).not.toBeInTheDocument()
      })
    })

    it('shows "New File" option in context menu', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')!
      fireEvent.contextMenu(fileItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        expect(screen.getByText('New File')).toBeInTheDocument()
      })
    })

    it('shows copy path options', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')!
      fireEvent.contextMenu(fileItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        expect(screen.getByText('Copy Relative Path')).toBeInTheDocument()
        expect(screen.getByText('Copy Path')).toBeInTheDocument()
      })
    })

    it('closes context menu on outside click', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')!
      fireEvent.contextMenu(fileItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        expect(screen.getByText('Rename')).toBeInTheDocument()
      })

      fireEvent.click(document)

      await waitFor(() => {
        expect(screen.queryByText('Rename')).not.toBeInTheDocument()
      })
    })
  })

  describe('Rename', () => {
    it('shows rename input when rename is selected', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')!
      fireEvent.contextMenu(fileItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        fireEvent.click(screen.getByText('Rename'))
      })

      await waitFor(() => {
        expect(screen.getByDisplayValue('README.md')).toBeInTheDocument()
      })
    })

    it('renames file on Enter', async () => {
      setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: {} },
        '/api/file/rename': { ok: true },
      })

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')!
      fireEvent.contextMenu(fileItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        fireEvent.click(screen.getByText('Rename'))
      })

      await waitFor(() => {
        const input = screen.getByDisplayValue('README.md')
        fireEvent.change(input, { target: { value: 'RENAMED.md' } })
        fireEvent.keyDown(input, { key: 'Enter' })
      })

      await vi.advanceTimersByTimeAsync(100)

      expect(defaultProps.onFileRenamed).toHaveBeenCalled()
    })

    it('cancels rename on Escape', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')!
      fireEvent.contextMenu(fileItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        fireEvent.click(screen.getByText('Rename'))
      })

      await waitFor(() => {
        const input = screen.getByDisplayValue('README.md')
        fireEvent.keyDown(input, { key: 'Escape' })
      })

      // Input should be gone
      await waitFor(() => {
        expect(screen.queryByDisplayValue('README.md')).not.toBeInTheDocument()
      })
    })
  })

  describe('Delete', () => {
    it('confirms before deleting', async () => {
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')!
      fireEvent.contextMenu(fileItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        fireEvent.click(screen.getByText('Delete'))
      })

      expect(confirmSpy).toHaveBeenCalledWith('Delete file "README.md"?')

      confirmSpy.mockRestore()
    })

    it('deletes file when confirmed', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true)

      setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: {} },
        // The delete endpoint should be handled
      })

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')!
      fireEvent.contextMenu(fileItem, { clientX: 100, clientY: 100 })

      await waitFor(() => {
        fireEvent.click(screen.getByText('Delete'))
      })

      await vi.advanceTimersByTimeAsync(100)

      expect(defaultProps.onFileDeleted).toHaveBeenCalledWith('README.md')
    })
  })

  describe('New File', () => {
    it('shows new file input when creatingFile prop is true', async () => {
      render(<FileTree {...defaultProps} creatingFile={true} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('filename')).toBeInTheDocument()
      })
    })

    it('creates file on Enter', async () => {
      setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: {} },
        '/api/file': {},
      })

      render(<FileTree {...defaultProps} creatingFile={true} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        const input = screen.getByPlaceholderText('filename')
        fireEvent.change(input, { target: { value: 'new-file.md' } })
        fireEvent.keyDown(input, { key: 'Enter' })
      })

      await vi.advanceTimersByTimeAsync(100)

      expect(defaultProps.onFileCreated).toHaveBeenCalled()
    })

    it('calls onCancelCreate on Escape', async () => {
      render(<FileTree {...defaultProps} creatingFile={true} />)

      await vi.advanceTimersByTimeAsync(100)

      await waitFor(() => {
        const input = screen.getByPlaceholderText('filename')
        fireEvent.keyDown(input, { key: 'Escape' })
      })

      expect(defaultProps.onCancelCreate).toHaveBeenCalled()
    })
  })

  describe('Drag and Drop', () => {
    it('sets draggable on file items', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const fileItem = screen.getByText('README.md').closest('.file-item')
      expect(fileItem).toHaveAttribute('draggable', 'true')
    })

    it('shows drag-over state on directory', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const srcDir = screen.getByText('src').closest('.file-item')!

      fireEvent.dragOver(srcDir, {
        dataTransfer: {
          getData: () => '',
          setData: () => {},
          dropEffect: 'move',
        },
      })

      await waitFor(() => {
        expect(srcDir).toHaveClass('drag-over')
      })
    })

    it('removes drag-over state on drag leave', async () => {
      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const srcDir = screen.getByText('src').closest('.file-item')!

      fireEvent.dragOver(srcDir, {
        dataTransfer: { getData: () => '', setData: () => {}, dropEffect: 'move' },
      })
      fireEvent.dragLeave(srcDir)

      await waitFor(() => {
        expect(srcDir).not.toHaveClass('drag-over')
      })
    })
  })

  describe('Polling', () => {
    it('polls for file tree changes', async () => {
      const fetchMock = setupApiMocks({
        '/api/tree': { entries: fileTree.root },
        '/api/git/status': { available: true, files: {} },
      })

      render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      const initialCalls = fetchMock.mock.calls.filter((call) =>
        call[0].includes('/api/tree')
      ).length

      // Wait for tree polling interval (3000ms)
      await vi.advanceTimersByTimeAsync(3500)

      const afterPollingCalls = fetchMock.mock.calls.filter((call) =>
        call[0].includes('/api/tree')
      ).length

      expect(afterPollingCalls).toBeGreaterThan(initialCalls)
    })

    it('cleans up polling intervals on unmount', async () => {
      const clearIntervalSpy = vi.spyOn(global, 'clearInterval')

      const { unmount } = render(<FileTree {...defaultProps} />)

      await vi.advanceTimersByTimeAsync(100)

      unmount()

      expect(clearIntervalSpy).toHaveBeenCalled()
    })
  })
})
