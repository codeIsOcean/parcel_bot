<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '@/composables/useLocale'
import { useTelegram } from '@/composables/useTelegram'
import { useChatsStore } from '@/stores/chats'
import PageHeader from '@/components/layout/PageHeader.vue'

const router = useRouter()
const { t } = useLocale()
const { haptic } = useTelegram()
const chatsStore = useChatsStore()

// Загрузка списка чатов при монтировании
onMounted(() => {
  chatsStore.fetchChats()
})

// Форматирование времени последнего сообщения
const formatTime = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  // Сегодня — показываем время
  if (diff < 86400000 && date.getDate() === now.getDate()) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  // Вчера
  if (diff < 172800000) {
    return t('yesterday')
  }
  // Старше — показываем дату
  return date.toLocaleDateString([], { day: '2-digit', month: '2-digit' })
}

// Переход в чат
const openChat = (chat) => {
  haptic.impact('light')
  router.push({ name: 'chat', params: { id: chat.chat_id } })
}
</script>

<template>
  <div class="chat-list-page">
    <!-- Заголовок -->
    <PageHeader :title="t('chats_title')" />

    <!-- Загрузка -->
    <div v-if="chatsStore.loading" class="chats-list">
      <div v-for="i in 4" :key="i" class="chat-item-skeleton">
        <div class="skeleton" style="width: 48px; height: 48px; border-radius: 50%"></div>
        <div style="flex: 1">
          <div class="skeleton" style="width: 60%; height: 14px; margin-bottom: 6px"></div>
          <div class="skeleton" style="width: 80%; height: 12px"></div>
        </div>
      </div>
    </div>

    <!-- Список чатов -->
    <div v-else-if="chatsStore.chatList.length > 0" class="chats-list">
      <div
        v-for="chat in chatsStore.chatList"
        :key="chat.chat_id"
        class="chat-item"
        @click="openChat(chat)"
      >
        <!-- Аватар собеседника -->
        <div class="chat-avatar">
          <img v-if="chat.partner_avatar" :src="chat.partner_avatar" alt="" class="avatar-img" />
          <span v-else class="avatar-letter">{{ (chat.partner_name || '?')[0].toUpperCase() }}</span>
        </div>

        <!-- Информация о чате -->
        <div class="chat-body">
          <!-- Имя и время -->
          <div class="chat-top">
            <span class="chat-name">{{ chat.partner_name }}</span>
            <span class="chat-time">{{ formatTime(chat.last_message_time) }}</span>
          </div>
          <!-- Последнее сообщение и бейдж непрочитанных -->
          <div class="chat-bottom">
            <span class="chat-last-message">{{ chat.last_message || t('no_messages') }}</span>
            <span v-if="chat.unread_count > 0" class="unread-badge">
              {{ chat.unread_count }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Пустое состояние -->
    <div v-else class="empty-state">
      <span class="empty-icon">💬</span>
      <p class="empty-text">{{ t('no_chats') }}</p>
      <p class="empty-hint">{{ t('no_chats_hint') }}</p>
    </div>
  </div>
</template>

<style scoped>
.chat-list-page {
  padding-bottom: 80px;
}

/* Список чатов */
.chats-list {
  padding: 0 16px;
}

/* Элемент чата */
.chat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  cursor: pointer;
  border-bottom: 1px solid #1C1C1E;
  transition: background 0.15s;
}

.chat-item:active {
  background: rgba(108, 92, 231, 0.05);
}

.chat-item:last-child {
  border-bottom: none;
}

/* Аватар */
.chat-avatar {
  position: relative;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
}

.avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-letter {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: #6C5CE7;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
}

/* Индикатор онлайн */
.online-dot {
  position: absolute;
  bottom: 1px;
  right: 1px;
  width: 12px;
  height: 12px;
  background: #30D158;
  border-radius: 50%;
  border: 2px solid #000;
}

/* Содержимое чата */
.chat-body {
  flex: 1;
  min-width: 0;
}

.chat-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.chat-name {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-time {
  font-size: 12px;
  color: #8E8E93;
  flex-shrink: 0;
  margin-left: 8px;
}

.chat-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-last-message {
  font-size: 13px;
  color: #8E8E93;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

/* Бейдж непрочитанных сообщений */
.unread-badge {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: #6C5CE7;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-left: 8px;
}

/* Скелетон загрузки */
.chat-item-skeleton {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
}

/* Пустое состояние */
.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 16px;
  color: #fff;
  font-weight: 600;
  margin-bottom: 6px;
}

.empty-hint {
  font-size: 13px;
  color: #8E8E93;
}
</style>
