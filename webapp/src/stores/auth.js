import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'

/**
 * Store авторизации — управление JWT токеном и данными пользователя.
 */
export const useAuthStore = defineStore('auth', () => {
  // JWT токен
  const token = ref(localStorage.getItem('parcel_bot_token') || '')

  // Данные пользователя
  const user = ref(null)

  // Текущая роль (sender / traveler)
  const role = ref(localStorage.getItem('parcel_bot_role') || 'sender')

  // Авторизован ли пользователь
  const isAuthenticated = computed(() => !!token.value)

  /**
   * Авторизация через Telegram initData.
   */
  const login = async (initData) => {
    const data = await authApi.login(initData)
    // Сохраняем токены
    token.value = data.token
    localStorage.setItem('parcel_bot_token', data.token)
    if (data.refresh_token) {
      localStorage.setItem('parcel_bot_refresh_token', data.refresh_token)
    }
    // Сохраняем пользователя
    user.value = data.user
  }

  /**
   * Загрузить данные текущего пользователя.
   */
  const fetchMe = async () => {
    try {
      const data = await authApi.getMe()
      user.value = data
    } catch (err) {
      // Если interceptor уже обработал refresh и получил новый токен — повторный запрос пройдёт.
      // Если refresh тоже не удался — interceptor уже очистил токены и сделал редирект.
      // Очищаем user только если токен действительно отсутствует после обработки.
      if (!localStorage.getItem('parcel_bot_token')) {
        user.value = null
      }
    }
  }

  /**
   * Переключить роль (отправитель / перевозчик).
   */
  const switchRole = (newRole) => {
    role.value = newRole
    localStorage.setItem('parcel_bot_role', newRole)
  }

  /**
   * Выход из аккаунта.
   */
  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('parcel_bot_token')
    localStorage.removeItem('parcel_bot_refresh_token')
  }

  return {
    token,
    user,
    role,
    isAuthenticated,
    login,
    fetchMe,
    switchRole,
    logout,
  }
})
