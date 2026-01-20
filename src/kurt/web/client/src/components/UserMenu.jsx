import { useState, useRef, useEffect } from 'react'

/**
 * UserMenu - Avatar with dropdown menu for user and workspace actions
 *
 * Props:
 * - email: User email for avatar letter and display
 * - workspaceName: Workspace name to display
 * - workspaceId: Workspace ID for actions
 */
export default function UserMenu({ email, workspaceName, workspaceId }) {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef(null)

  // Get first letter of email (uppercase) for avatar
  const avatarLetter = email ? email.charAt(0).toUpperCase() : '?'

  // Show workspace name if available (not a UUID)
  const showWorkspace = workspaceName && !workspaceName.includes('-')

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // TODO: implement workspace management navigation
  const handleManageWorkspace = () => {
    console.log('Manage workspace clicked', workspaceId)
    setIsOpen(false)
  }

  return (
    <div className="user-menu" ref={menuRef}>
      <button
        className="user-avatar"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="User menu"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {avatarLetter}
      </button>

      {isOpen && (
        <div className="user-menu-dropdown" role="menu">
          <div className="user-menu-email">{email}</div>
          {showWorkspace && <div className="user-menu-workspace">workspace: {workspaceName}</div>}
          <div className="user-menu-divider" />
          <button
            className="user-menu-item"
            onClick={handleManageWorkspace}
            role="menuitem"
          >
            Manage workspace
          </button>
        </div>
      )}
    </div>
  )
}
