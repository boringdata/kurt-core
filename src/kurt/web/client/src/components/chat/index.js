// Chat Components - Claude Code VSCode Extension Clone
// Using assistant-ui primitives

// Core Layout
export { default as ChatPanel, chatThemeVars } from './ChatPanel'
export { default as MessageList, EmptyState, Messages, ScrollToBottom } from './MessageList'

// Messages
export { default as UserMessage } from './UserMessage'
export { default as AssistantMessage, AssistantLoading, AssistantInterrupted, assistantMessageStyles } from './AssistantMessage'

// Content Renderers
export { default as TextBlock } from './TextBlock'

// Tool Renderers (to be implemented)
// export { default as ToolUseBlock } from './tools/ToolUseBlock'
// export { default as ReadToolRenderer } from './tools/ReadToolRenderer'
// export { default as BashToolRenderer } from './tools/BashToolRenderer'
// export { default as WriteToolRenderer } from './tools/WriteToolRenderer'
// export { default as EditToolRenderer } from './tools/EditToolRenderer'
// export { default as GlobToolRenderer } from './tools/GlobToolRenderer'
// export { default as GrepToolRenderer } from './tools/GrepToolRenderer'

// Interaction (to be implemented)
// export { default as PermissionPanel } from './PermissionPanel'
// export { default as InputArea } from './InputArea'
// export { default as SessionHeader } from './SessionHeader'
