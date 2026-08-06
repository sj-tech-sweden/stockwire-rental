<template>
  <div class="assistant-drawer">
    <div class="assistant-header row items-center q-pa-sm q-gutter-sm">
      <q-icon name="smart_toy" size="24px" color="primary" />
      <div class="col text-subtitle2">{{ t('assistant.title') }}</div>
      <q-badge :color="isStreaming ? 'warning' : 'positive'" :label="isStreaming ? t('assistant.thinking') : t('assistant.online')" />
      <q-btn flat dense round icon="delete_sweep" size="sm" @click="clearChat" :aria-label="t('assistant.clearChat')" />
      <q-btn flat dense round icon="close" size="sm" @click="assistantStore.close()" :aria-label="t('app.actions.close')" />
    </div>

    <q-separator />

    <div ref="scrollAreaRef" class="assistant-scroll-area">
      <div v-if="!messages.length" class="assistant-empty">
        <q-icon name="smart_toy" size="48px" color="grey-5" class="q-mb-md" />
        <div class="text-subtitle2 text-grey-6 q-mb-xs">{{ t('assistant.welcome') }}</div>
        <div class="text-caption text-grey-5">{{ t('assistant.hint') }}</div>
      </div>

      <div v-for="msg in messages" :key="msg.id" class="assistant-message" :class="`assistant-message--${msg.role}`">
        <div class="row items-start no-wrap q-gutter-xs">
          <q-avatar :color="msg.role === 'user' ? 'primary' : 'teal'" text-color="white" size="32px">
            <q-icon :name="msg.role === 'user' ? 'person' : 'smart_toy'" size="16px" />
          </q-avatar>
          <div class="col">
            <div class="text-caption text-grey-5 q-mb-xs">
              {{ msg.role === 'user' ? t('assistant.you') : t('assistant.assistant') }} · {{ formatTime(msg.timestamp) }}
            </div>
            <div v-if="msg.toolCalls?.length" class="q-mb-xs">
              <div v-for="(tc, idx) in msg.toolCalls" :key="idx" class="row items-center q-gutter-xs q-mb-xs">
                <q-chip
                  :color="tc.status === 'done' ? 'positive' : tc.status === 'running' ? 'warning' : 'grey'"
                  text-color="white"
                  size="sm"
                  icon="build"
                >
                  {{ tc.tool }}({{ formatToolArgs(tc.args) }})
                </q-chip>
              </div>
            </div>
            <div v-if="msg.text" class="assistant-text" v-html="formatText(msg.text)" />
            <q-spinner v-if="msg.isStreaming && !msg.text" size="16px" color="teal" class="q-mt-xs" />
          </div>
        </div>
      </div>
    </div>

    <q-separator />

    <div class="assistant-footer row items-center q-pa-sm q-gutter-xs">
      <q-input
        ref="inputRef"
        v-model="inputText"
        :placeholder="t('assistant.placeholder')"
        dense
        outlined
        class="col"
        @keyup.enter="send"
        :disable="isStreaming"
      />
      <q-btn
        color="primary"
        round
        icon="send"
        :disable="!inputText.trim() || isStreaming"
        :loading="isStreaming"
        @click="send"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAssistantStore } from '../stores/assistantStore'

const { t } = useI18n()
const assistantStore = useAssistantStore()

const inputText = ref('')
const inputRef = ref(null)
const scrollAreaRef = ref(null)

const messages = computed(() => assistantStore.messages)
const isStreaming = computed(() => assistantStore.isStreaming)

function send() {
  if (!inputText.value.trim() || isStreaming.value) return
  assistantStore.sendMessage(inputText.value)
  inputText.value = ''
}

function clearChat() {
  assistantStore.clearChat()
}

function formatTime(date) {
  if (!date) return ''
  return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatText(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
}

function formatToolArgs(args) {
  if (!args || typeof args !== 'object') return ''
  return Object.entries(args).map(([k, v]) => `${k}=${v}`).join(', ')
}

watch(() => assistantStore.isOpen, (open) => {
  if (open) {
    setTimeout(() => inputRef.value?.focus(), 300)
  }
})
</script>

<style scoped>
.assistant-drawer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--q-dark-page, #fff);
}

.assistant-header {
  min-height: 48px;
  background: var(--q-dark-page, #fff);
}

.assistant-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.assistant-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
}

.assistant-message {
  margin-bottom: 12px;
}

.assistant-text {
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.assistant-text :deep(code) {
  background: var(--q-grey-3, #e0e0e0);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 13px;
}

.assistant-footer {
  background: var(--q-dark-page, #fff);
}
</style>
