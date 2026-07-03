import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatsApi } from '@/api/chats'

/**
 * Store чатов — список чатов и сообщения.
 */
export const useChatsStore = defineStore('chats', () => {
  // Список чатов
  const chatList = ref([])

  // Сообщения текущего чата
  const messages = ref([])

  // ID текущего открытого чата
  const activeChatId = ref(null)

  // Загрузка
  const loading = ref(false)

  /**
   * Загрузить список чатов.
   */
  const fetchChats = async () => {
    loading.value = true
    try {
      const data = await chatsApi.getMyChats()
      chatList.value = data.items || data
    } catch {
      // Ошибка загрузки чатов
    } finally {
      loading.value = false
    }
  }

  /**
   * Загрузить сообщения чата.
   */
  const fetchMessages = async (chatId) => {
    activeChatId.value = chatId
    const data = await chatsApi.getMessages(chatId)
    messages.value = data.items || data
  }

  /**
   * Отправить сообщение.
   */
  const sendMessage = async (chatId, text) => {
    const msg = await chatsApi.sendMessage(chatId, { text })
    // Добавляем в конец списка
    messages.value.push(msg)
    return msg
  }

  return {
    chatList,
    messages,
    activeChatId,
    loading,
    fetchChats,
    fetchMessages,
    sendMessage,
  }
})
