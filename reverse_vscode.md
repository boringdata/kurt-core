# Reverse Engineering Claude Code VSCode Extension

## Location

```
~/.vscode/extensions/anthropic.claude-code-2.1.7-darwin-arm64/
```

## Key Files

| File | Description |
|------|-------------|
| `extension.js` | Main bundled/minified code (~1.2MB) |
| `package.json` | Extension manifest |
| `claude-code-settings.schema.json` | Settings schema |

---

## 1. CLI Interaction

### CLI Flags Discovered

```bash
grep -o '\-\-[a-zA-Z-]*' extension.js | sort -u
```

| Flag | Purpose |
|------|---------|
| `--input-format stream-json` | Realtime streaming input |
| `--output-format stream-json` | Realtime streaming output |
| `--verbose` | Required for stream-json output |
| `--permission-mode` | Set permission mode |
| `--resume <session-id>` | Resume existing session |
| `--continue` | Continue conversation |
| `--fork-session` | Fork an existing session |
| `--resume-session-at` | Resume at specific point |
| `--no-session-persistence` | Disable persistence |
| `--include-partial-messages` | Stream partial messages |
| `--allowedTools` | Comma-separated allowed tools |
| `--disallowedTools` | Comma-separated blocked tools |
| `--max-thinking-tokens` | Thinking budget |
| `--max-turns` | Max conversation turns |
| `--max-budget-usd` | Cost limit |
| `--model` | Model selection |
| `--mcp-config` | MCP server configuration |
| `--settings` | Custom settings file |
| `--setting-sources` | user, project, local |

### Process Spawning

```javascript
spawn(command, args, {
  cwd: workingDir,
  stdio: ["pipe", "pipe", "pipe"],
  signal: abortController.signal,
  env: environment,
  windowsHide: true
})
```

**Key insight**: Process stays alive - stdin kept open for multiple messages.

---

## 2. Message Protocol

### User Message Format

```json
{
  "type": "user",
  "session_id": "",
  "message": {
    "role": "user",
    "content": [
      {"type": "text", "text": "your message"}
    ]
  }
}
```

### Image Content Block

**IMPORTANT: Use Anthropic API format (NOT simplified format)**

```json
{
  "type": "image",
  "source": {
    "type": "base64",
    "media_type": "image/png",
    "data": "<base64-encoded-data>"
  }
}
```

**Full content with image:**
```json
{
  "type": "user",
  "session_id": "",
  "message": {
    "role": "user",
    "content": [
      {"type": "text", "text": "What is in this image?"},
      {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBORw0..."}}
    ]
  }
}
```

### Response Types

| Type | Subtype | Description |
|------|---------|-------------|
| `system` | `init` | Session initialization |
| `assistant` | - | Claude's response |
| `result` | `success` | Turn completed |
| `result` | `exit` | Process exited |

---

## 3. Permission Mode / Mode Switching

### Mode Mapping

| UI Mode | --permission-mode |
|---------|------------------|
| ask | `default` |
| act | `acceptEdits` |
| plan | `plan` |

`bypassPermissions` exists, but VSCode UI only exposes it when
`allowDangerouslySkipPermissions` is enabled.

### How Mode Change Works

1. Mode is set via `--permission-mode` at CLI startup (initialPermissionMode)
2. Extension can switch mid-session via a `control_request` subtype `set_permission_mode`
3. If a restart is needed, the extension uses `--resume` to preserve history

### Code Pattern

```javascript
spawnClaude(input, resume, canUseTool, model, cwd, permissionMode, allowSkip, maxThinkingTokens, mcpServers)
```

---

## 4. Slash Commands

### Discovery

Extension calls `supportedCommands()` on the CLI to get available commands:

```javascript
config: {
  slashCommands: await query.supportedCommands(),
  models: await query.supportedModels(),
  accountInfo: await query.accountInfo()
}
```

### Sending Slash Commands

Slash commands are sent as regular user messages:

```json
{
  "type": "user",
  "session_id": "",
  "message": {
    "role": "user",
    "content": [{"type": "text", "text": "/compact"}]
  }
}
```

The CLI interprets messages starting with `/` as commands.

---

## 5. File Context (@)

### @ File References

Files are passed as context by:
1. Reading file content
2. Including in message content

**Pattern in extension:**
```javascript
// Files added to context via UI get read and included
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [
      {"type": "text", "text": "@src/file.ts explain this file"},
      // Or file content is expanded inline
    ]
  }
}
```

The CLI handles `@path` syntax and expands file references.

---

## 6. Tool Permission Handling

### Permission Request Flow

1. CLI sends `control_request` message via stdout
2. SDK/Extension shows UI dialog
3. User decision sent back via stdin as `control_response`

### Key Flag: --permission-prompt-tool

The CLI supports interactive permission prompts via the `--permission-prompt-tool` flag:

```bash
--permission-prompt-tool stdio
```

When this flag is set to `stdio`:
- CLI sends `control_request` messages for permission decisions
- Host must respond with `control_response` messages via stdin
- Without this flag, CLI auto-denies or uses terminal prompts

### Control Request Format (CLI → Host)

```json
{
  "type": "control_request",
  "request_id": "uuid-here",
  "request": {
    "subtype": "can_use_tool",
    "tool_name": "Write",
    "input": {
      "file_path": "/path/to/file.txt",
      "content": "..."
    },
    "permission_suggestions": [
      {
        "type": "addRules",
        "rules": [{"toolName": "Bash", "ruleContent": "Bash:rm *"}],
        "destination": "session"
      },
      {
        "type": "addDirectories",
        "directories": ["/path/to/project"],
        "destination": "session"
      },
      {
        "type": "setMode",
        "mode": "acceptEdits",
        "destination": "session"
      }
    ],
    "tool_use_id": "toolu_xxx"
  }
}
```

### Permission Destination Labels

| Destination | UI Label | Tooltip |
|-------------|----------|---------|
| `localSettings` | this project (just you) | Saves to `.claude/settings.local.json` (gitignored) |
| `userSettings` | all projects | Saves to `~/.claude/settings.json` |
| `projectSettings` | this project (shared) | Saves to `.claude/settings.json` (shared with team) |
| `session` | this session | Only for this session (not saved) |
| `cliArg` | CLI | From command line arguments |

### Control Response Format (Host → CLI)

```json
{
  "type": "control_response",
  "response": {
    "subtype": "success",
    "request_id": "uuid-here",
    "response": {
      "behavior": "allow",
      "updatedInput": {
        "file_path": "/path/to/file.txt",
        "content": "..."
      },
      "permission_suggestions": [
        {"type": "addRules", "rules": [{"toolName": "Bash", "ruleContent": "Bash:rm *"}], "destination": "session"}
      ]
    }
  }
}
```

For a deny response, set `"behavior": "deny"` and include a `"message"` string.
Always include `updatedInput` for allow-like decisions.

### SDK Code Pattern

```javascript
if (canUseTool) {
  args.push("--permission-prompt-tool", "stdio")
}
```

### Tool Control Flags

```bash
--allowedTools Bash,Read,Write,Edit
--disallowedTools WebSearch,WebFetch
```

---

## 7. Session Management

### Session Operations

| Operation | Implementation |
|-----------|----------------|
| New session | Start CLI with `--session-id <uuid>` |
| Resume | Start CLI with `--resume <session-id>` |
| Fork | `--fork-session` flag |
| Rewind | `query.rewindFiles(userMessageId, {dryRun})` |

### Fork Conversation

```javascript
case "fork_conversation":
  return {
    type: "fork_conversation_response",
    sessionId: await sessions.forkSession(
      request.forkedFromSession,
      request.resumeSessionAt
    )
  }
```

---

## 8. Model & Thinking Settings

### Model Selection

```javascript
// Get available models
models: await query.supportedModels()

// Set model at startup
--model claude-sonnet-4-20250514
```

### Thinking Level

```javascript
getMaxThinkingTokensForModel(thinkingLevel) {
  // Maps thinking level to token count
}

// At startup
--max-thinking-tokens <count>
```

---

## 9. Interrupt / Cancel

### Interrupting Claude

```javascript
async interruptClaude(channelId) {
  let channel = this.channels.get(channelId)
  await channel.query.interrupt()
}
```

Uses `AbortController.signal` passed to process spawn.

---

## 10. File Updates & Checkpointing

### File Change Tracking

```javascript
hooks: {
  PreToolUse: [
    {matcher: "Edit|Write|MultiEdit", hooks: [captureBaseline]},
    {matcher: "Edit|Write|Read", hooks: [saveFileIfNeeded]}
  ],
  PostToolUse: [
    {matcher: "Edit|Write|MultiEdit", hooks: [findDiagnosticsProblems]}
  ]
}
```

### File Updated Event

```javascript
this.send({
  type: "file_updated",
  channelId: channelId,
  filePath: path,
  oldContent: oldContent,
  newContent: newContent
})
```

---

## 11. Environment Variables

```javascript
env.CLAUDE_CODE_ENTRYPOINT = "sdk-ts"
delete env.NODE_OPTIONS
delete env.DEBUG  // unless DEBUG_CLAUDE_AGENT_SDK
```

---

## 12. Channel Management

### Channel Structure

```javascript
this.channels.set(channelId, {
  in: inputQueue,        // AsyncQueue for messages
  query: claudeQuery,    // SDK query object
  pid: processId,        // Claude CLI process ID
  vscodeMcpServer: mcp,  // MCP server instance
  mcpServers: {},        // Additional MCP servers
  chromeMcpState: {status: "disconnected"}
})
```

### Message Flow

```javascript
// Incoming from client
case "io_message":
  this.transportMessage(channelId, message, done)

// Outgoing to client
for await (let message of query) {
  this.send({type: "io_message", channelId, message, done: false})
}
```

---

## 13. MCP (Model Context Protocol)

### MCP Server Config

```javascript
if (mcpServers && Object.keys(mcpServers).length > 0) {
  args.push("--mcp-config", JSON.stringify({mcpServers}))
}
```

### Built-in MCP Server

Extension provides `claude-vscode` MCP server for IDE integration.

---

## 14. Speech-to-Text

```javascript
case "start_speech_to_text":
  await this.handleStartSpeechToText(channelId)

case "stop_speech_to_text":
  this.handleStopSpeechToText(channelId)
```

---

## Summary: Key Implementation Details

### To Build a Native-like Experience:

1. **Keep CLI process alive** - Don't restart for each message
2. **Use stream-json format** - `--input-format stream-json --output-format stream-json --verbose`
3. **Message format** - Include `session_id: ""` and content as array
4. **Mode changes** - Restart with `--resume` to preserve history
5. **Slash commands** - Send as regular user messages with `/` prefix
6. **Images** - Use Anthropic format: `{type: "image", source: {type: "base64", media_type: "image/...", data: "<base64>"}}` in content array
7. **File context** - CLI handles `@path` syntax natively
8. **Interrupt** - Use AbortController signal on process
9. **Tools** - Control via `--allowedTools` and `--disallowedTools`

### Testing Interactive Mode

```bash
{
  echo '{"type":"user","session_id":"","message":{"role":"user","content":[{"type":"text","text":"Hello"}]}}'
  sleep 3
  echo '{"type":"user","session_id":"","message":{"role":"user","content":[{"type":"text","text":"What did I say?"}]}}'
} | claude --print --input-format stream-json --output-format stream-json --verbose
```

**Result**: CLI stays alive and maintains conversation context!

---

## Development Workflow for Replicating Features

When adding a new feature from the VSCode extension:

### 1. Check Source Code

Search the extension.js for relevant patterns:

```bash
# Find flags and parameters
strings ~/.vscode/extensions/anthropic.claude-code-*/extension.js | grep -E 'flag|param'

# Find message types
strings ~/.vscode/extensions/anthropic.claude-code-*/extension.js | grep -E '"type":|type:'
```

### 2. Test Directly with CLI

**ALWAYS test CLI behavior before implementing frontend/backend.**

```bash
# Basic bidirectional test with named pipes
cat > /tmp/test-feature.sh << 'SCRIPT'
#!/bin/bash
echo '{"type":"user","session_id":"","message":{"role":"user","content":[{"type":"text","text":"Your test prompt"}]}}'
while IFS= read -r line; do
  echo "GOT: $line" >&2
  # Check for expected message type and respond
  if echo "$line" | grep -q '"type":"expected_type"'; then
    request_id=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['request_id'])")
    # Send response
    echo '{"type":"response_type","request_id":"'$request_id'",...}'
  fi
  if echo "$line" | grep -q '"type":"result"'; then
    break
  fi
done
SCRIPT
chmod +x /tmp/test-feature.sh

mkfifo /tmp/in /tmp/out
/tmp/test-feature.sh < /tmp/out | claude [flags] > /tmp/out 2>&1 &
sleep 20; kill $! 2>/dev/null; rm -f /tmp/in /tmp/out
```

### 3. Implement in Backend (stream_bridge.py)

- Add flag to `build_stream_args()` if needed
- Handle incoming messages in read loop
- Handle outgoing responses in WebSocket handler

### 4. Implement in Frontend (ClaudeStreamChat.jsx)

- Detect message type in `adapter.messages()` generator
- Call `onStreamingChange()` with event
- Handle event in `handleStreamingChange()`
- Send response via `sendApprovalResponse()` or similar

### 5. Document

Update this file with discovered formats and patterns.

---

## Verified Message Formats

### Control Request (Permission Prompt)

**CLI → Host:**
```json
{
  "type": "control_request",
  "request_id": "uuid",
  "request": {
    "subtype": "can_use_tool",
    "tool_name": "Write",
    "input": {"file_path": "...", "content": "..."},
    "permission_suggestions": [...],
    "tool_use_id": "toolu_xxx"
  }
}
```

**Host → CLI (Allow):**
```json
{
  "type": "control_response",
  "response": {
    "subtype": "success",
    "request_id": "uuid",
    "response": {
      "behavior": "allow",
      "updatedInput": {"file_path": "...", "content": "..."}
    }
  }
}
```

**Host → CLI (Deny):**
```json
{
  "type": "control_response",
  "response": {
    "subtype": "success",
    "request_id": "uuid",
    "response": {
      "behavior": "deny",
      "message": "User denied permission"
    }
  }
}
```

**IMPORTANT:** `updatedInput` MUST contain the original tool input for "allow" responses, or the tool will fail with validation errors.
