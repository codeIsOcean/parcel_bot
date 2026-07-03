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
   * Получить заявки на мой рейс.
   */
  getRequests: (flightId) =>
    api.get(`/flights/${flightId}/requests`),

  /**
   * Принять/отклонить заявку.
   */
  respondToRequest: (flightId, requestId, action) =>
    api.post(`/flights/${flightId}/requests/${requestId}/${action}`),
}
