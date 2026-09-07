import api from './client'

/**
 * API для работы с рейсами перевозчиков.
 */
export const flightsApi = {
  /**
   * Поиск рейсов по маршруту.
   */
  search: (params = {}) =>
    api.get('/flights', { params }),

  /**
   * Мои рейсы (для перевозчика).
   */
  getMyFlights: (params = {}) =>
    api.get('/flights/my', { params }),

  /**
   * Опубликовать новый рейс.
   */
  create: (data) =>
    api.post('/flights', data),

  /**
   * Получить детали рейса.
   */
  getById: (id) =>
    api.get(`/flights/${id}`),

  /**
   * Популярные маршруты: сколько активных рейсов идёт по каждому.
   */
  getPopularRoutes: (limit = 6) =>
    api.get('/flights/popular-routes', { params: { limit } }),


  /**
   * Отменить свой рейс.
   */
  cancel: (id) =>
    api.post(`/flights/${id}/cancel`),
}
