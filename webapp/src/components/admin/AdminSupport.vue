<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { adminApi } from '@/api/admin'

const route = useRoute()
const { t } = useLocale()
const { haptic } = useTelegram()

// Вкладка инбокса: открытые или архив
const status = ref('open')

// Список обращений
const sessions = ref([])
const loading = ref(false)
const error = ref('')

// Открытый тред: обращение и его сообщения
const opened = ref(null)
const messages = ref([])
const draft = ref('')
const sending = ref(false)
const threadError = ref('')

// Ссылка на список сообщений для прокрутки вниз
const messagesEl = ref(null)

// Таймеры опроса
let listTimer = null
let threadTimer = null

// Дата и время в коротком виде
const fmtTime = (value) => (value ? new Date(value).toLocaleString('ru-RU') : '')

// Загрузка списка обращений
const loadSessions = async (silent = false) => {
  if (!silent) loading.value = true
  try {
    sessions.value = (await adminApi.supportSessions(status.value)).items
    error.value = ''
  } catch {
    if (!silent) error.value = t('admin_error')
  } finally {
    loading.value = false
  }
}

// Прокрутить переписку вниз
const scrollDown = async () => {
  await nextTick()
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}

// Загрузка сообщений открытого треда
const loadMessages = async () => {
  if (!opened.value) return
  try {
    const before = messages.value.length
    messages.value = (await adminApi.supportMessages(opened.value.user_id)).items
    if (messages.value.length !== before) scrollDown()
  } catch {
    threadError.value = t('admin_error')
  }
}

// Смена вкладки
const setStatus = (s) => {
  haptic.selection()
  status.value = s
  loadSessions()
}

// Открыть тред и запустить опрос сообщений
const openThread = async (session) => {
  haptic.impact('light')
  opened.value = session
  messages.value = []
  threadError.value = ''
  await loadMessages()
  clearInterval(threadTimer)
  threadTimer = setInterval(loadMessages, 3000)
}

// Закрыть тред
const closeThread = () => {
  clearInterval(threadTimer)
  threadTimer = null
  opened.value = null
  loadSessions(true)
}

// Отправить ответ пользователю
const send = async () => {
  const text = draft.value.trim()
  if (!text || sending.value || !opened.value) return
  haptic.impact('medium')
  sending.value = true
  threadError.value = ''
  try {
    await adminApi.supportReply(opened.value.user_id, text)
    draft.value = ''
    await loadMessages()
    haptic.notification('success')
  } catch (e) {
    haptic.notification('error')
    const code = e?.response?.data?.detail
    threadError.value = code === 'no_ticket' ? t('admin_support_no_ticket') : t('admin_error')
  } finally {
    sending.value = false
  }
}

// Отправить обращение в архив
const archive = async () => {
  if (!opened.value) return
  try {
    await adminApi.supportClose(opened.value.user_id)
    haptic.notification('success')
    closeThread()
  } catch {
    haptic.notification('error')
    threadError.value = t('admin_error')
  }
}

onMounted(async () => {
  await loadSessions()
  // Опрос списка, пока раздел открыт
  listTimer = setInterval(() => loadSessions(true), 5000)

  // Диплинк ?thread=<user_id> открывает переписку сразу
  const threadId = Number(route.query.thread)
  if (threadId) {
    let session = sessions.value.find((s) => s.user_id === threadId)
    // Обращение могло уйти в архив — ищем среди всех
    if (!session) {
      try {
        session = (await adminApi.supportSessions('all')).items.find((s) => s.user_id === threadId)
      } catch {
        session = null
      }
    }
    if (session) openThread(session)
  }
})

// Таймеры чистим при уходе с раздела
onUnmounted(() => {
  clearInterval(listTimer)
  clearInterval(threadTimer)
})
</script>

<template>
  <div class="support">
    <!-- Тред -->
    <template v-if="opened">
      <div class="thread-header">
        <button class="back-btn" @click="closeThread">‹</button>
        <div class="thread-user">
          <span class="thread-name">{{ opened.user_name }}</span>
          <span class="thread-sub">{{ opened.username ? '@' + opened.username : '#' + opened.user_id }}</span>
        </div>
        <button v-if="opened.is_active" class="btn btn-sm btn-secondary" @click="archive">{{ t('admin_support_archive') }}</button>
      </div>

      <!-- Сообщения -->
      <div ref="messagesEl" class="messages">
        <p v-if="!messages.length" class="muted">{{ t('admin_empty') }}</p>
        <div
          v-for="m in messages"
          :key="m.id"
          class="bubble"
          :class="m.sender_role === 'admin' ? 'bubble-admin' : 'bubble-user'"
        >
          <p class="bubble-text">{{ m.text }}</p>
          <span class="bubble-time">{{ fmtTime(m.created_at) }}</span>
        </div>
      </div>

      <p v-if="threadError" class="error-text">{{ threadError }}</p>

      <!-- Ответ -->
      <div class="composer">
        <textarea v-model="draft" class="input textarea" :placeholder="t('admin_support_reply_placeholder')" rows="2"></textarea>
        <button class="btn btn-primary" :disabled="sending || !draft.trim()" @click="send">
          {{ t('admin_support_send') }}
        </button>
      </div>
    </template>

    <!-- Инбокс -->
    <template v-else>
      <div class="chips">
        <button class="chip" :class="{ active: status === 'open' }" @click="setStatus('open')">{{ t('admin_support_open') }}</button>
        <button class="chip" :class="{ active: status === 'archived' }" @click="setStatus('archived')">{{ t('admin_support_archived') }}</button>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>
      <p v-if="loading" class="muted">{{ t('admin_loading') }}</p>
      <p v-else-if="!sessions.length" class="muted">{{ t('admin_support_empty') }}</p>

      <!-- Карточка обращения -->
      <div v-for="s in sessions" :key="s.id" class="card session-card" @click="openThread(s)">
        <div class="session-top">
          <span class="session-name">{{ s.user_name }}</span>
          <span v-if="s.is_pending" class="badge badge-yellow">{{ t('admin_support_pending') }}</span>
          <span v-else-if="!s.is_active" class="badge badge-purple">{{ t('admin_support_archived') }}</span>
        </div>
        <div class="session-meta">
          <span>{{ s.username ? '@' + s.username : '#' + s.user_id }} · {{ s.message_count }} 💬</span>
          <span>{{ fmtTime(s.updated_at) }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.support {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chips {
  display: flex;
  gap: 6px;
}

.session-card {
  padding: 12px;
  cursor: pointer;
}

.session-card:active {
  transform: scale(0.98);
}

.session-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.session-name {
  font-size: 15px;
  font-weight: 600;
}

.session-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-2);
}

/* Шапка треда */
.thread-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.back-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: var(--surface-2);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}

.thread-user {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.thread-name {
  font-size: 15px;
  font-weight: 600;
}

.thread-sub {
  font-size: 12px;
  color: var(--text-2);
}

/* Переписка */
.messages {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 50vh;
  overflow-y: auto;
  padding: 4px 0;
}

.bubble {
  max-width: 85%;
  padding: 8px 12px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.bubble-user {
  align-self: flex-start;
  background: var(--surface);
  border: 1px solid var(--border);
}

.bubble-admin {
  align-self: flex-end;
  background: var(--primary);
  color: var(--on-accent);
}

.bubble-text {
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

.bubble-time {
  font-size: 10px;
  opacity: 0.7;
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.textarea {
  resize: none;
}

.btn:disabled {
  opacity: 0.5;
}

.btn-sm {
  padding: 8px 12px;
  font-size: 13px;
}

.error-text {
  color: var(--danger);
  font-size: 13px;
}

.muted {
  color: var(--text-2);
  font-size: 13px;
}
</style>
