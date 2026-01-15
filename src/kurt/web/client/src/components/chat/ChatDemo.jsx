import { useState } from 'react'
import { AssistantRuntimeProvider, useLocalRuntime, ThreadPrimitive, ComposerPrimitive } from '@assistant-ui/react'
import ChatPanel, { chatThemeVars } from './ChatPanel'
import MessageList, { Messages, EmptyState } from './MessageList'
import UserMessage from './UserMessage'
import AssistantMessage, { assistantMessageStyles } from './AssistantMessage'
import ToolUseBlock from './ToolUseBlock'
import ReadToolRenderer from './ReadToolRenderer'
import BashToolRenderer from './BashToolRenderer'
import WriteToolRenderer from './WriteToolRenderer'
import EditToolRenderer from './EditToolRenderer'
import GlobToolRenderer from './GlobToolRenderer'
import GrepToolRenderer from './GrepToolRenderer'
import PermissionPanel from './PermissionPanel'
import InputArea from './InputArea'
import SessionHeader from './SessionHeader'

/**
 * ChatDemo - Demo page for testing chat components
 * Access via ?poc=chat in the URL
 */

// ChatModelAdapter with run function
const MockChatAdapter = {
  async *run({ messages, abortSignal }) {
    // Simulate typing delay
    await new Promise((resolve) => setTimeout(resolve, 500))

    if (abortSignal?.aborted) return

    // Get the last user message
    const lastUserMessage = messages
      .filter((m) => m.role === 'user')
      .pop()

    const userText = lastUserMessage?.content
      ?.filter((c) => c.type === 'text')
      .map((c) => c.text)
      .join(' ') || 'something'

    // Yield a text response
    const responseText = `I received your message: "${userText}". This is a demo response from the mock adapter.`

    yield {
      content: [
        {
          type: 'text',
          text: responseText,
        },
      ],
    }
  },
}

// Sample data for InputArea
const sampleFiles = [
  { name: 'CAPTURE_GUIDE.md', path: 'CAPTURE_GUIDE.md', isDirectory: false },
  { name: 'PROGRESS.md', path: 'PROGRESS.md', isDirectory: false },
  { name: 'RALPH_PROMPT.md', path: 'RALPH_PROMPT.md', isDirectory: false },
  { name: 'reference/', path: 'reference/', isDirectory: true },
]

const sampleCommands = [
  {
    label: 'Context',
    items: [
      { id: 'attach', label: 'Attach file...' },
      { id: 'mention', label: 'Mention file from this project...' },
      { id: 'clear', label: 'Clear conversation' },
    ],
  },
  {
    label: 'Model',
    items: [
      { id: 'switch', label: 'Switch model...', value: 'Opus' },
      { id: 'thinking', label: 'Thinking', toggle: false },
    ],
  },
]

// Thread component using assistant-ui primitives
const Thread = () => {
  return (
    <ChatPanel>
      <MessageList>
        <EmptyState />
        <Messages
          components={{
            UserMessage: UserMessage,
            AssistantMessage: AssistantMessage,
          }}
        />
      </MessageList>
      <InputArea
        files={sampleFiles}
        commands={sampleCommands}
        onFileSelect={(file) => console.log('File selected:', file)}
        onCommandSelect={(cmd) => console.log('Command selected:', cmd)}
      />
    </ChatPanel>
  )
}

// Simple composer for input
const Composer = () => {
  return (
    <ComposerPrimitive.Root
      style={{
        padding: 'var(--chat-spacing-md, 12px)',
        borderTop: '1px solid var(--chat-border, #454545)',
      }}
    >
      <div
        style={{
          display: 'flex',
          gap: '8px',
          alignItems: 'center',
          backgroundColor: 'var(--chat-input-bg, #3c3c3c)',
          borderRadius: 'var(--chat-radius-md, 8px)',
          padding: '10px 12px',
        }}
      >
        <ComposerPrimitive.Input
          placeholder="Type a message..."
          style={{
            flex: 1,
            backgroundColor: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--chat-text, #cccccc)',
            fontSize: '14px',
            fontFamily: 'inherit',
            resize: 'none',
            lineHeight: '1.4',
          }}
          rows={1}
          maxRows={8}
          autoFocus
        />
        <ComposerPrimitive.Send
          style={{
            backgroundColor: '#ae5630',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            width: '32px',
            height: '32px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <span>↑</span>
        </ComposerPrimitive.Send>
      </div>
    </ComposerPrimitive.Root>
  )
}

// Tool Demo Section - Shows static demos of tool renderers
const ToolDemoSection = () => (
  <div
    style={{
      padding: 'var(--chat-spacing-lg, 16px)',
      borderTop: '1px solid var(--chat-border, #454545)',
    }}
  >
    <h3
      style={{
        color: 'var(--chat-text, #cccccc)',
        fontSize: '14px',
        fontWeight: 600,
        marginBottom: 'var(--chat-spacing-md, 12px)',
      }}
    >
      Tool Renderers Demo
    </h3>

    {/* Read Tool Demo */}
    <ReadToolRenderer
      filePath="src/components/App.jsx"
      content={`import React from 'react'
import { render } from 'react-dom'

function App() {
  return <div>Hello World</div>
}

export default App`}
      status="complete"
      lineCount={8}
    />

    {/* Bash Tool Demo - Success */}
    <BashToolRenderer
      command="ls -la"
      description="List files in current directory"
      output={`total 24
drwxr-xr-x  8 user staff  256 Jan 14 11:52 .
drwxr-xr-x  3 user staff   96 Jan 13 20:42 ..
-rw-r--r--  1 user staff 2302 Jan 14 11:52 PROGRESS.md
-rw-r--r--  1 user staff  192 Jan 14 10:05 reference/`}
      exitCode={0}
      status="complete"
    />

    {/* Bash Tool Demo - Error */}
    <BashToolRenderer
      command="cat nonexistent.txt"
      description="Read file contents"
      error="cat: nonexistent.txt: No such file or directory"
      exitCode={1}
      status="error"
    />

    {/* Read Tool Demo - Error */}
    <ReadToolRenderer
      filePath="/etc/shadow"
      error="Permission denied: Cannot read /etc/shadow"
      status="error"
    />

    {/* Write Tool Demo */}
    <WriteToolRenderer
      filePath="test.txt"
      content="Hello World!\nThis is a test file."
      status="complete"
      lineCount={2}
    />

    {/* Edit Tool Demo */}
    <EditToolRenderer
      filePath="config.js"
      linesAdded={2}
      linesRemoved={1}
      diff={`--- a/config.js
+++ b/config.js
@@ -1,3 +1,4 @@
-const debug = false
+const debug = true
+const logLevel = 'verbose'
 module.exports = { debug }`}
      status="complete"
    />

    {/* Glob Tool Demo - With Results */}
    <GlobToolRenderer
      pattern="**/*.jsx"
      files={[
        'src/App.jsx',
        'src/components/ChatPanel.jsx',
        'src/components/UserMessage.jsx',
        'src/components/AssistantMessage.jsx',
      ]}
      status="complete"
    />

    {/* Glob Tool Demo - No Results */}
    <GlobToolRenderer
      pattern="**/*.py"
      files={[]}
      status="complete"
    />

    {/* Grep Tool Demo */}
    <GrepToolRenderer
      pattern="useState"
      results={[
        {
          file: 'src/App.jsx',
          matches: [
            { line: 3, content: "import { useState, useEffect } from 'react'" },
            { line: 15, content: '  const [count, setCount] = useState(0)' },
          ],
        },
        {
          file: 'src/hooks/useAuth.js',
          matches: [
            { line: 5, content: '  const [user, setUser] = useState(null)' },
          ],
        },
      ]}
      status="complete"
    />
  </div>
)

// Interaction Demo Section - Shows Phase 3 components
const InteractionDemoSection = () => {
  const [permissionSelected, setPermissionSelected] = useState(0)

  return (
    <div
      style={{
        padding: 'var(--chat-spacing-lg, 16px)',
        borderTop: '1px solid var(--chat-border, #454545)',
      }}
    >
      <h3
        style={{
          color: 'var(--chat-text, #cccccc)',
          fontSize: '14px',
          fontWeight: 600,
          marginBottom: 'var(--chat-spacing-md, 12px)',
        }}
      >
        Interaction Components Demo
      </h3>

      {/* Session Header Demo */}
      <div style={{ marginBottom: '24px' }}>
        <h4 style={{ color: 'var(--chat-text-muted)', fontSize: '12px', marginBottom: '8px' }}>
          SessionHeader
        </h4>
        <div style={{ border: '1px solid var(--chat-border, #454545)', borderRadius: '8px', overflow: 'hidden' }}>
          <SessionHeader
            title="This is a test message"
            onTitleClick={() => console.log('Title clicked')}
            onNewSession={() => console.log('New session')}
          />
        </div>
      </div>

      {/* Permission Panel Demo */}
      <div style={{ marginBottom: '24px' }}>
        <h4 style={{ color: 'var(--chat-text-muted)', fontSize: '12px', marginBottom: '8px' }}>
          PermissionPanel
        </h4>
        <PermissionPanel
          title="Make this edit to PROGRESS.md?"
          options={[
            { label: 'Yes' },
            { label: 'Yes, allow all edits this session' },
            { label: 'No' },
          ]}
          selectedIndex={permissionSelected}
          onSelect={(option) => setPermissionSelected(option?.index ?? 0)}
          onCustomResponse={(text) => console.log('Custom:', text)}
        />
      </div>

      {/* InputArea is now integrated in the main Thread above */}
    </div>
  )
}

// Main demo component
const ChatDemo = () => {
  const runtime = useLocalRuntime(MockChatAdapter)

  return (
    <>
      <style>{chatThemeVars}</style>
      <style>{assistantMessageStyles}</style>
      <div
        style={{
          width: '100vw',
          height: '100vh',
          backgroundColor: 'var(--chat-bg, #1e1e1e)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Chat section - fixed height for internal scrolling */}
        <div style={{ height: '50vh', minHeight: '300px', display: 'flex', flexDirection: 'column' }}>
          <AssistantRuntimeProvider runtime={runtime}>
            <Thread />
          </AssistantRuntimeProvider>
        </div>
        {/* Demo sections - scrollable */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <ToolDemoSection />
          <InteractionDemoSection />
        </div>
      </div>
    </>
  )
}

export default ChatDemo
