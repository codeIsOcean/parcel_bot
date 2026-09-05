import api from './client'

/**
 * API чата с поддержкой.
 */
export const supportApi = {
  /**
   * Переписка с администратором.
   */
  getMessages: () =>
    api.get('/support/messages'),

  /**
   * Сколько ответов ещё не прочитано.
   */
  getUnread: () =>
    api.get('/support/unread'),

  /**
   * Написать в поддержку.
   */
  send: (text) =>
    api.post('/support/messages', { text }),
}
