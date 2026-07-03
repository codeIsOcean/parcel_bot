import api from './client'

/**
 * API для relay-чата.
 */
export const chatsApi = {
  /**
   * Получить список моих чатов.
   */
  getMyChats: () =>
    api.get('/chats'),

  /**
   * Получить сообщения чата.
   */
  getMessages: (chatId, params = {}) =>
    api.get(`/chats/${chatId}/messages`, { params }),

  /**
   * Отправить сообщение в чат.
   */
  sendMessage: (chatId, data) =>
    api.post(`/chats/${chatId}/messages`, data),

  /**
   * Предложить цену (counter-offer).
   */
  offerPrice: (chatId, price) =>
    api.post(`/chats/${chatId}/offer`, { price }),
}
