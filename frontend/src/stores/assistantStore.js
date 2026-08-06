import { defineStore } from 'pinia'
import { ref, nextTick } from 'vue'
import { getApiBaseUrl } from '../utils/runtime-config'
import { useAuthStore } from './auth'

export const useAssistantStore = defineStore('assistant', () => {
  const isOpen = ref(false)
  const messages = ref([])
  const isStreaming = ref(false)

  function toggle() {
    isOpen.value = !isOpen.value
  }

  function open() {
    isOpen.value = true
  }

  function close() {
    isOpen.value = false
  }

  async function sendMessage(text) {
    if (!text.trim() || isStreaming.value) return

    messages.value.push({
      id: Date.now(),
      role: 'user',
      text: text.trim(),
      timestamp: new Date(),
    })

    const assistantMsg = {
      id: Date.now() + 1,
      role: 'assistant',
      text: '',
      timestamp: new Date(),
      isStreaming: true,
      toolCalls: [],
    }
    messages.value.push(assistantMsg)
    isStreaming.value = true

    await nextTick()
    scrollToBottom()

    try {
      const authStore = useAuthStore()
      const payload = {
        messages: messages.value
          .filter(m => !m.isStreaming)
          .map(m => ({ role: m.role, content: m.text })),
      }

      const response = await fetch(`${getApiBaseUrl()}/api/v1/assistant/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.token}`,
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') break

          try {
            const parsed = JSON.parse(data)
            if (parsed.type === 'text') {
              assistantMsg.text += parsed.content
              await nextTick()
              scrollToBottom()
            } else if (parsed.type === 'tool_call') {
              assistantMsg.toolCalls.push({
                tool: parsed.tool,
                args: parsed.args,
                status: 'running',
              })
            } else if (parsed.type === 'tool_result') {
              const tc = assistantMsg.toolCalls.find(
                t => t.tool === parsed.tool
              )
              if (tc) {
                tc.result = parsed.result
                tc.status = 'done'
              }
            } else if (parsed.type === 'error') {
              assistantMsg.text += `\n\nError: ${parsed.content}`
            }
          } catch {
            // Skip malformed JSON
          }
        }

        await nextTick()
        scrollToBottom()
      }
    } catch (err) {
      assistantMsg.text += `\n\n${err.message || 'Connection failed'}`
    } finally {
      assistantMsg.isStreaming = false
      isStreaming.value = false
      await nextTick()
      scrollToBottom()
    }
  }

  function scrollToBottom() {
    nextTick(() => {
      const el = document.querySelector('.assistant-scroll-area')
      if (el) el.scrollTop = el.scrollHeight
    })
  }

  function clearChat() {
    messages.value = []
  }

  return {
    isOpen,
    messages,
    isStreaming,
    toggle,
    open,
    close,
    sendMessage,
    clearChat,
  }
})
