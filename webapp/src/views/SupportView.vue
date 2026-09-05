<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { supportApi } from '@/api/support'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useLocale()
const { haptic } = useTelegram()

const loading = ref(true)
const available = ref(true)
const messages = ref([])
const draft = ref('')
const sending = ref(false)
const error = ref('')
const listRef = ref(null)

// Переписка обновляется опросом, пока экран открыт
let pollTimer = null
const POLL_INTERVAL_MS = 10000

// Прокрутка к последнему сообщению
const scrollToBottom = async () => {
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

// Загрузка переписки
const load = async (scroll = true) => {
  try {
    const data = await supportApi.getMessages()
    messages.value = data.items || []
    available.value = data.available
    if (scroll) await scrollToBottom()
  } catch {
    error.value = t('error_loading')
  } finally {
    loading.value = false
  }
}

// Отправка сообщения
const send = async () => {
  const text = draft.value.trim()
  if (!text || sending.value) return

  sending.value = true
  error.value = ''
  draft.value = ''
  haptic.impact('light')

  try {
    const message = await supportApi.send(text)
    messages.value.push(message)
    await scrollToBottom()
  } catch (e) {
    // 503 — администраторы не заданы, писать некому
    if (e?.response?.status === 503) {
      available.value = false
      error.value = t('support_unavailable')
    } else {
      error.value = t('error_generic')
    }
    // Возвращаем текст, чтобы человек не потерял написанное
    draft.value = text
  } finally {
    sending.value = false
  }
}

// Время сообщения
const formatTime = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  await load()
  pollTimer = setInterval(() => load(false), POLL_INTERVAL_MS)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="support-view">
    <PageHeader :title="t('support_title')" show-back />

    <div v-if="loading" class="state">{{ t('loading') }}</div>

    <template v-else>
      <!-- Переписка -->
      <div ref="listRef" class="messages">
        <div v-if="!messages.length" class="state empty">
          <div class="empty-icon">🆘</div>
          <div>{{ t('support_empty') }}</div>
        </div>

        <div
          v-for="message in messages"
          :key="message.id"
          class="message"
          :class="message.role"
        >
          <div class="bubble">
            <div class="author">
              {{ message.role === 'admin' ? t('support_admin') : t('support_you') }}
            </div>
            <div class="text">{{ message.text }}</div>
            <div class="time">{{ formatTime(message.created_at) }}</div>
          </div>
        </div>
      </div>

      <!-- Ошибка -->
      <div v-if="error" class="error-bar">{{ error }}</div>

      <!-- Ввод -->
      <div class="input-bar">
        <input
          v-model="draft"
          class="input"
          :placeholder="t('support_placeholder')"
          :disabled="!available"
          @keyup.enter="send"
        />
        <button class="send-btn" :disabled="sending || !available || !draft.trim()" @click="send">
          ➤
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.support-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.state {
  padding: 40px 16px;
  text-align: center;
  color: var(--text-2);
  font-size: 14px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 10px;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px 12px;
}

.message {
  display: flex;
  margin-bottom: 8px;
}

.message.user {
  justify-content: flex-end;
}

.message.admin {
  justify-content: flex-start;
}

.bubble {
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 14px;
  background: var(--surface-2);
}

.message.user .bubble {
  background: var(--primary);
  border-bottom-right-radius: 4px;
}

.message.admin .bubble {
  border-bottom-left-radius: 4px;
}

.author {
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 2px;
  color: var(--text-2);
}

.message.user .author {
  color: rgba(255, 255, 255, 0.75);
}

.text {
  font-size: 14px;
  line-height: 1.4;
  color: var(--text-1);
  word-wrap: break-word;
}

.message.user .text {
  color: var(--on-accent);
}

.time {
  font-size: 10px;
  text-align: right;
  margin-top: 2px;
  color: var(--text-3);
}

.message.user .time {
  color: rgba(255, 255, 255, 0.65);
}

.error-bar {
  margin: 0 16px 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 59, 48, 0.1);
  color: var(--danger);
  font-size: 12px;
  text-align: center;
}

.input-bar {
  display: flex;
  gap: 8px;
  padding: 10px 16px calc(10px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--border);
  background: var(--surface);
}

.input {
  flex: 1;
  padding: 11px 14px;
  border: 1px solid var(--border-strong);
  border-radius: 20px;
  background: var(--surface-2);
  color: var(--text-1);
  font-size: 15px;
}

.input:disabled {
  opacity: 0.6;
}

.send-btn {
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 50%;
  background: var(--primary);
  color: var(--on-accent);
  font-size: 16px;
  cursor: pointer;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
