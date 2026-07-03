import api from './client'

/**
 * API для подписок — тарифные планы, оплата, история.
 */
export const subscriptionsApi = {
  /**
   * Получить активную подписку пользователя.
   */
  getActive: () => api.get('/subscriptions/active'),

  /**
   * Создать подписку (оплата).
   */
  create: (data) => api.post('/subscriptions', data),

  /**
   * Получить историю подписок.
   */
  getHistory: () => api.get('/subscriptions/history'),

  /**
   * Получить цены на тарифные планы.
   */
  getPrices: () => api.get('/subscriptions/prices'),
}
