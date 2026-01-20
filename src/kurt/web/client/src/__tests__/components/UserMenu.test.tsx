/**
 * Tests for UserMenu component
 *
 * Features tested:
 * - Avatar rendering with email initial
 * - Dropdown open/close behavior
 * - Click outside to close
 * - Workspace name display
 * - Accessibility attributes
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import UserMenu from '../../components/UserMenu'

describe('UserMenu', () => {
  const defaultProps = {
    email: 'john@example.com',
    workspaceName: 'My Workspace',
    workspaceId: 'ws-123',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Avatar Rendering', () => {
    it('renders first letter of email as avatar', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      expect(avatar).toHaveTextContent('J')
    })

    it('renders uppercase letter for avatar', () => {
      render(<UserMenu {...defaultProps} email="alice@example.com" />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      expect(avatar).toHaveTextContent('A')
    })

    it('renders question mark when email is empty', () => {
      render(<UserMenu {...defaultProps} email="" />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      expect(avatar).toHaveTextContent('?')
    })

    it('renders question mark when email is undefined', () => {
      render(<UserMenu {...defaultProps} email={undefined as unknown as string} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      expect(avatar).toHaveTextContent('?')
    })
  })

  describe('Dropdown Toggle', () => {
    it('dropdown is closed by default', () => {
      render(<UserMenu {...defaultProps} />)

      expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    })

    it('opens dropdown when avatar is clicked', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(screen.getByRole('menu')).toBeInTheDocument()
    })

    it('closes dropdown when avatar is clicked again', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar) // Open
      fireEvent.click(avatar) // Close

      expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    })

    it('closes dropdown when clicking outside', () => {
      render(
        <div>
          <UserMenu {...defaultProps} />
          <button data-testid="outside">Outside</button>
        </div>
      )

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)
      expect(screen.getByRole('menu')).toBeInTheDocument()

      fireEvent.mouseDown(screen.getByTestId('outside'))
      expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    })

    it('does not close when clicking inside dropdown', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      const dropdown = screen.getByRole('menu')
      fireEvent.mouseDown(dropdown)

      expect(screen.getByRole('menu')).toBeInTheDocument()
    })
  })

  describe('Dropdown Content', () => {
    it('displays user email', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(screen.getByText('john@example.com')).toBeInTheDocument()
    })

    it('displays workspace name when available', () => {
      render(<UserMenu {...defaultProps} workspaceName="My Workspace" />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(screen.getByText('workspace: My Workspace')).toBeInTheDocument()
    })

    it('hides workspace when name looks like UUID', () => {
      render(<UserMenu {...defaultProps} workspaceName="9459aaea-4d1e-4933-88f9-538646f60e7e" />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      // Should not show UUID as workspace name
      expect(screen.queryByText(/9459aaea/)).not.toBeInTheDocument()
    })

    it('displays manage workspace button', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(screen.getByRole('menuitem', { name: 'Manage workspace' })).toBeInTheDocument()
    })

    it('closes dropdown when manage workspace is clicked', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})

      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      const manageButton = screen.getByRole('menuitem', { name: 'Manage workspace' })
      fireEvent.click(manageButton)

      expect(screen.queryByRole('menu')).not.toBeInTheDocument()
      expect(consoleSpy).toHaveBeenCalledWith('Manage workspace clicked', 'ws-123')

      consoleSpy.mockRestore()
    })
  })

  describe('Accessibility', () => {
    it('has correct aria-label on avatar button', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      expect(avatar).toHaveAttribute('aria-label', 'User menu')
    })

    it('has aria-expanded false when closed', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      expect(avatar).toHaveAttribute('aria-expanded', 'false')
    })

    it('has aria-expanded true when open', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(avatar).toHaveAttribute('aria-expanded', 'true')
    })

    it('has aria-haspopup attribute', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      expect(avatar).toHaveAttribute('aria-haspopup', 'true')
    })

    it('dropdown has role menu', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(screen.getByRole('menu')).toBeInTheDocument()
    })

    it('menu items have role menuitem', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      const menuItems = screen.getAllByRole('menuitem')
      expect(menuItems).toHaveLength(1) // Manage workspace
    })
  })

  describe('CSS Classes', () => {
    it('applies user-menu class to container', () => {
      render(<UserMenu {...defaultProps} />)

      expect(document.querySelector('.user-menu')).toBeInTheDocument()
    })

    it('applies user-avatar class to button', () => {
      render(<UserMenu {...defaultProps} />)

      expect(document.querySelector('.user-avatar')).toBeInTheDocument()
    })

    it('applies user-menu-dropdown class when open', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(document.querySelector('.user-menu-dropdown')).toBeInTheDocument()
    })

    it('applies user-menu-email class to email', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(document.querySelector('.user-menu-email')).toBeInTheDocument()
    })

    it('applies user-menu-workspace class when workspace name available', () => {
      render(<UserMenu {...defaultProps} workspaceName="My Workspace" />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(document.querySelector('.user-menu-workspace')).toBeInTheDocument()
    })

    it('applies user-menu-divider class', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(document.querySelector('.user-menu-divider')).toBeInTheDocument()
    })

    it('applies user-menu-item class to menu items', () => {
      render(<UserMenu {...defaultProps} />)

      const avatar = screen.getByRole('button', { name: 'User menu' })
      fireEvent.click(avatar)

      expect(document.querySelector('.user-menu-item')).toBeInTheDocument()
    })
  })
})
