/**
 * SessionHeader - Displays current session title with controls
 *
 * From reference screenshots:
 * - Title with dropdown arrow for session selector
 * - "+" button on the right for new conversation
 * - Clean horizontal layout with border below
 */

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 16px',
    borderBottom: '1px solid var(--chat-border)',
    backgroundColor: 'var(--chat-bg)',
  },
  titleButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 8px',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    borderRadius: 'var(--chat-radius-sm, 4px)',
  },
  title: {
    color: 'var(--chat-text)',
    fontSize: '14px',
    fontWeight: 400,
  },
  dropdown: {
    color: 'var(--chat-text-muted)',
    fontSize: '12px',
  },
  newButton: {
    width: '28px',
    height: '28px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
    border: 'none',
    color: 'var(--chat-text)',
    fontSize: '18px',
    cursor: 'pointer',
    borderRadius: 'var(--chat-radius-sm, 4px)',
  },
}

const SessionHeader = ({
  title = 'New conversation',
  onTitleClick,
  onNewSession,
  showDropdown = true,
}) => {
  return (
    <div style={styles.container}>
      {/* Session title with dropdown */}
      <button onClick={onTitleClick} style={styles.titleButton}>
        <span style={styles.title}>{title}</span>
        {showDropdown && <span style={styles.dropdown}>˅</span>}
      </button>

      {/* New session button */}
      <button onClick={onNewSession} style={styles.newButton} title="New conversation">
        +
      </button>
    </div>
  )
}

export default SessionHeader
