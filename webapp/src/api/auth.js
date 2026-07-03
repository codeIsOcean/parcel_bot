import api from './client'

/**
 * API авторизации через Telegram initData.
 */
export const authApi = {
  /**
   * Авторизация — отправляем initData, получаем JWT.
   */
  login: (initData) =>
    api.post('/auth/login', { init_data: initData }),

  /**
   * Получить текущего пользователя.
   */
  getMe: () =>
    api.get('/auth/me'),
}
