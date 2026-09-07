import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import { usersApi } from '@/api/users'

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

  // Администратор (владелец из .env или назначенный из панели)
  const isAdmin = computed(() => !!user.value?.is_admin)

  // Телефон подтверждён — без него сделки недоступны
  const hasPhone = computed(() => !!user.value?.phone)

  /**
   * Подхватить режим из профиля: сервер помнит последний выбор.
   */
  const applyServerRole = (data) => {
    if (data?.role === 'sender' || data?.role === 'traveler') {
      role.value = data.role
      localStorage.setItem('parcel_bot_role', data.role)
    }
  }

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
    applyServerRole(data.user)
  }

  /**
   * Загрузить данные текущего пользователя.
   */
  const fetchMe = async () => {
    try {
      // /users/me отдаёт приватные поля: телефон, признак админа, баланс
      const data = await usersApi.getMe()
      user.value = data
      applyServerRole(data)
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
    // Сервер запоминает режим, чтобы уведомления и следующий вход были по нему
    if (token.value) {
      usersApi.updateProfile({ role: newRole }).catch(() => {})
    }
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
    isAdmin,
    hasPhone,
    login,
    fetchMe,
    switchRole,
    logout,
  }
})
