"use client"

import '@/components/chat-2/styles.css'
import {
  ActionBarPrimitive,
  AssistantIf,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  AssistantRuntimeProvider,
  useLocalRuntime,
} from "@assistant-ui/react"
import { MarkdownText } from "@/components/assistant-ui/markdown-text"
import {
  ArrowUpIcon,
  ChevronDownIcon,
  PlusIcon,
  RefreshCwIcon,
  CopyIcon,
  PencilIcon,
  ThumbsUpIcon,
  ThumbsDownIcon,
  SettingsIcon,
} from "lucide-react"
import type { FC } from "react"

// Claude official styling
export const Claude: FC = () => {
  return (
    <ThreadPrimitive.Root className="flex h-full flex-col items-stretch bg-[#F5F5F0] p-4 pt-16 font-serif dark:bg-[#2b2a27]">
      <ThreadPrimitive.Viewport className="flex grow flex-col overflow-y-scroll">
        <ThreadPrimitive.Messages components={{ Message: ChatMessage }} />
        <div aria-hidden="true" className="h-4" />
      </ThreadPrimitive.Viewport>

      <ComposerPrimitive.Root className="mx-auto flex w-full max-w-3xl flex-col rounded-2xl border border-transparent bg-white p-0.5 shadow-[0_0.25rem_1.25rem_rgba(0,0,0,0.035),0_0_0_0.5px_rgba(0,0,0,0.08)] transition-shadow duration-200 focus-within:shadow-[0_0.25rem_1.25rem_rgba(0,0,0,0.075),0_0_0_0.5px_rgba(0,0,0,0.15)] hover:shadow-[0_0.25rem_1.25rem_rgba(0,0,0,0.05),0_0_0_0.5px_rgba(0,0,0,0.12)] dark:bg-[#1f1e1b] dark:shadow-[0_0.25rem_1.25rem_rgba(0,0,0,0.4),0_0_0_0.5px_rgba(108,106,96,0.15)] dark:hover:shadow-[0_0.25rem_1.25rem_rgba(0,0,0,0.4),0_0_0_0.5px_rgba(108,106,96,0.3)] dark:focus-within:shadow-[0_0.25rem_1.25rem_rgba(0,0,0,0.5),0_0_0_0.5px_rgba(108,106,96,0.3)]">
        <div className="m-3.5 flex flex-col gap-3.5">
          <div className="relative">
            <div className="max-h-96 w-full overflow-y-auto">
              <ComposerPrimitive.Input
                placeholder="How can I help you today?"
                className="block min-h-6 w-full resize-none bg-transparent text-[#1a1a18] outline-none placeholder:text-[#9a9893] dark:text-[#eee] dark:placeholder:text-[#9a9893]"
              />
            </div>
          </div>
          <div className="flex w-full items-center gap-2">
            <div className="relative flex min-w-0 flex-1 shrink items-center gap-2">
              <ComposerPrimitive.AddAttachment className="flex h-8 min-w-8 items-center justify-center overflow-hidden rounded-lg border border-[#00000015] bg-transparent px-1.5 text-[#6b6a68] transition-all hover:bg-[#f5f5f0] hover:text-[#1a1a18] active:scale-[0.98] dark:border-[#6c6a6040] dark:text-[#9a9893] dark:hover:bg-[#393937] dark:hover:text-[#eee]">
                <PlusIcon className="size-4" />
              </ComposerPrimitive.AddAttachment>
              <button
                type="button"
                className="flex h-8 min-w-8 items-center justify-center overflow-hidden rounded-lg border border-[#00000015] bg-transparent px-1.5 text-[#6b6a68] transition-all hover:bg-[#f5f5f0] hover:text-[#1a1a18] active:scale-[0.98] dark:border-[#6c6a6040] dark:text-[#9a9893] dark:hover:bg-[#393937] dark:hover:text-[#eee]"
                aria-label="Open tools menu"
              >
                <SettingsIcon className="size-4" />
              </button>
            </div>
            <button
              type="button"
              className="flex h-8 min-w-16 items-center justify-center gap-1 whitespace-nowrap rounded-md px-2 pr-2 pl-2.5 text-[#1a1a18] text-xs transition duration-300 hover:bg-[#f5f5f0] active:scale-[0.985] dark:text-[#eee] dark:hover:bg-[#393937]"
            >
              <span className="font-serif text-[14px]">Claude Code</span>
              <ChevronDownIcon className="size-5 opacity-75" />
            </button>
            <ComposerPrimitive.Send className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#ae5630] transition-colors hover:bg-[#c4633a] active:scale-95 disabled:pointer-events-none disabled:opacity-50 dark:bg-[#ae5630] dark:hover:bg-[#c4633a]">
              <ArrowUpIcon className="size-4 text-white" />
            </ComposerPrimitive.Send>
          </div>
        </div>
      </ComposerPrimitive.Root>
    </ThreadPrimitive.Root>
  )
}

const ChatMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="group relative mx-auto mt-1 mb-1 block w-full max-w-3xl">
      <MessagePrimitive.If user>
        <div className="group/user relative inline-flex max-w-[75ch] flex-col gap-2 rounded-xl bg-[#DDD9CE] py-2.5 pr-6 pl-2.5 text-[#1a1a18] transition-all dark:bg-[#393937] dark:text-[#eee]">
          <div className="relative flex flex-row gap-2">
            <div className="shrink-0 self-start">
              <div className="flex h-7 w-7 shrink-0 select-none items-center justify-center rounded-full bg-[#1a1a18] font-bold text-[12px] text-white dark:bg-[#eee] dark:text-[#2b2a27]">
                U
              </div>
            </div>
            <div className="flex-1">
              <div className="relative grid grid-cols-1 gap-2 py-0.5">
                <div className="whitespace-pre-wrap">
                  <MessagePrimitive.Content />
                </div>
              </div>
            </div>
          </div>
          <div className="pointer-events-none absolute right-2 bottom-0">
            <ActionBarPrimitive.Root
              autohide="not-last"
              className="pointer-events-auto min-w-max translate-x-1 translate-y-4 rounded-lg border-[#00000015] border-[0.5px] bg-white/80 p-0.5 opacity-0 shadow-sm backdrop-blur-sm transition group-hover/user:translate-x-0.5 group-hover/user:opacity-100 dark:border-[#6c6a6040] dark:bg-[#1f1e1b]/80"
            >
              <div className="flex items-center text-[#6b6a68] dark:text-[#9a9893]">
                <ActionBarPrimitive.Reload className="flex h-8 w-8 items-center justify-center rounded-md transition hover:bg-transparent active:scale-95">
                  <RefreshCwIcon className="size-5" />
                </ActionBarPrimitive.Reload>
                <ActionBarPrimitive.Edit className="flex h-8 w-8 items-center justify-center rounded-md transition hover:bg-transparent active:scale-95">
                  <PencilIcon className="size-5" />
                </ActionBarPrimitive.Edit>
              </div>
            </ActionBarPrimitive.Root>
          </div>
        </div>
      </MessagePrimitive.If>

      <MessagePrimitive.If assistant>
        <div className="relative mb-12 font-serif">
          <div className="relative leading-[1.65rem]">
            <div className="grid grid-cols-1 gap-2.5">
              <div className="whitespace-normal pr-8 pl-2 font-serif text-[#1a1a18] dark:text-[#eee]">
                <MessagePrimitive.Content components={{ Text: MarkdownText }} />
              </div>
            </div>
          </div>
          <div className="pointer-events-none absolute inset-x-0 bottom-0">
            <ActionBarPrimitive.Root
              hideWhenRunning
              autohide="not-last"
              className="pointer-events-auto flex w-full translate-y-full flex-col items-end px-2 pt-2 transition"
            >
              <div className="flex items-center text-[#6b6a68] dark:text-[#9a9893]">
                <ActionBarPrimitive.Copy className="flex h-8 w-8 items-center justify-center rounded-md transition hover:bg-transparent active:scale-95">
                  <CopyIcon className="size-5" />
                </ActionBarPrimitive.Copy>
                <ActionBarPrimitive.FeedbackPositive className="flex h-8 w-8 items-center justify-center rounded-md transition hover:bg-transparent active:scale-95">
                  <ThumbsUpIcon className="size-4" />
                </ActionBarPrimitive.FeedbackPositive>
                <ActionBarPrimitive.FeedbackNegative className="flex h-8 w-8 items-center justify-center rounded-md transition hover:bg-transparent active:scale-95">
                  <ThumbsDownIcon className="size-4" />
                </ActionBarPrimitive.FeedbackNegative>
                <ActionBarPrimitive.Reload className="flex h-8 w-8 items-center justify-center rounded-md transition hover:bg-transparent active:scale-95">
                  <RefreshCwIcon className="size-5" />
                </ActionBarPrimitive.Reload>
              </div>
              <AssistantIf condition={({ message }) => message.isLast}>
                <p className="mt-2 w-full text-right text-[#8a8985] text-[0.65rem] leading-[0.85rem] opacity-90 sm:text-[0.75rem] dark:text-[#b8b5a9]">
                  Claude can make mistakes. Please double-check responses.
                </p>
              </AssistantIf>
            </ActionBarPrimitive.Root>
          </div>
        </div>
      </MessagePrimitive.If>
    </MessagePrimitive.Root>
  )
}

// Claude Code runtime adapter - connects to stream-json output
function createClaudeAdapter(apiUrl: string) {
  return {
    async *run({ messages, abortSignal }: {
      messages: Array<{ role: string; content: Array<{ type: string; text?: string }> }>
      abortSignal?: AbortSignal
    }) {
      const lastMessage = messages[messages.length - 1]
      const userText = lastMessage?.content?.find(c => c.type === 'text')?.text || ''

      if (!userText.trim()) return

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userText }),
        signal: abortSignal,
      })

      if (!response.ok) {
        yield { content: [{ type: 'text' as const, text: `Error: ${response.statusText}` }] }
        return
      }

      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''
      let currentText = ''

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.trim()) continue
            try {
              const msg = JSON.parse(line)

              if (msg.type === 'assistant') {
                for (const content of msg.message?.content || []) {
                  if (content.type === 'text') {
                    currentText = content.text
                    yield { content: [{ type: 'text' as const, text: currentText }] }
                  }
                  if (content.type === 'tool_use') {
                    const toolText = `\n\n🔧 **${content.name}**\n\`\`\`json\n${JSON.stringify(content.input, null, 2)}\n\`\`\``
                    yield { content: [{ type: 'text' as const, text: currentText + toolText }] }
                  }
                }
              }

              if (msg.type === 'user' && msg.tool_use_result) {
                const stdout = msg.tool_use_result.stdout || ''
                const stderr = msg.tool_use_result.stderr || ''
                const output = (stdout + stderr).trim()
                if (output) {
                  const resultText = `\n\`\`\`\n${output.slice(0, 500)}${output.length > 500 ? '...' : ''}\n\`\`\`\n`
                  currentText += resultText
                  yield { content: [{ type: 'text' as const, text: currentText }] }
                }
              }

              if (msg.type === 'result' && msg.result) {
                yield { content: [{ type: 'text' as const, text: msg.result }] }
              }
            } catch {
              // Skip unparseable lines
            }
          }
        }
      } finally {
        reader.releaseLock()
      }
    }
  }
}

// Mock adapter for testing without backend
const MockAdapter = {
  async *run({ messages, abortSignal }: { messages: any[], abortSignal?: AbortSignal }) {
    const lastMessage = messages[messages.length - 1]
    const userText = lastMessage?.content?.[0]?.text || 'Hello'

    const response = `I received: "${userText}"\n\nThis is a **mock response**. Connect to Claude Code backend to get real responses.`

    for (let i = 0; i < response.length; i++) {
      if (abortSignal?.aborted) break
      yield { content: [{ type: 'text' as const, text: response.slice(0, i + 1) }] }
      await new Promise(r => setTimeout(r, 10))
    }
  },
}

interface Chat2Props {
  apiUrl?: string
  useMock?: boolean
}

export function Chat2({ apiUrl = '/api/claude', useMock = true }: Chat2Props) {
  const adapter = useMock ? MockAdapter : createClaudeAdapter(apiUrl)
  const runtime = useLocalRuntime(adapter)

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <Claude />
    </AssistantRuntimeProvider>
  )
}

// Re-export for compatibility
export const ClaudeThread = Claude
export default Chat2
