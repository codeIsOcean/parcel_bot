import api from './client'

/**
 * API жалоб на пользователей.
 */
export const reportsApi = {
  /**
   * Список причин жалобы.
   */
  getReasons: () =>
    api.get('/reports/reasons'),

  /**
   * Пожаловаться на пользователя.
   */
  create: (data) =>
    api.post('/reports', data),
}
