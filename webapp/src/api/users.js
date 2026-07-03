import api from './client'

/**
 * API для профилей пользователей.
 */
export const usersApi = {
  /**
   * Получить профиль пользователя.
   */
  getProfile: (userId) =>
    api.get(`/users/${userId}`),

  /**
   * Обновить свой профиль.
   */
  updateProfile: (data) =>
    api.put('/users/me', data),

  /**
   * Получить отзывы о пользователе.
   */
  getReviews: (userId, params = {}) =>
    api.get(`/users/${userId}/reviews`, { params }),

  /**
   * Оставить отзыв.
   */
  createReview: (userId, data) =>
    api.post(`/users/${userId}/reviews`, data),

  /**
   * Получить список городов.
   */
  getCities: () =>
    api.get('/cities'),

  /**
   * Предложить новый маршрут.
   */
  suggestRoute: (data) =>
    api.post('/routes/suggest', data),
}
