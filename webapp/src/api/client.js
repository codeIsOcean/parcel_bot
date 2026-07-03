import axios from 'axios'

// Единый API клиент для всех запросов к backend
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor: подставляем JWT токен в каждый запрос
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('parcel_bot_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Флаг для предотвращения повторных refresh-запросов
let isRefreshing = false
let failedQueue = []

// Обработка очереди запросов после refresh
const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token)
    }
  })
  failedQueue = []
}

// Interceptor: обработка ошибок ответов с автоматическим refresh токена
api.interceptors.response.use(
  // Успешный ответ — возвращаем data
  (response) => response.data,
  // Ошибка — обрабатываем
  async (error) => {
    const originalRequest = error.config

    // 401 — пробуем обновить токен
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Если уже идёт refresh — ставим запрос в очередь
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = localStorage.getItem('parcel_bot_refresh_token')
      if (!refreshToken) {
        // Нет refresh токена — очищаем авторизацию
        localStorage.removeItem('parcel_bot_token')
        processQueue(error, null)
        isRefreshing = false
        window.location.href = '/'
        return Promise.reject(error)
      }

      try {
        // Запрос на обновление токена
        const response = await axios.post(
          `${api.defaults.baseURL}/auth/refresh`,
          { refresh_token: refreshToken }
        )
        const newToken = response.data.token
        if (!newToken) {
          throw new Error('No token in refresh response')
        }
        localStorage.setItem('parcel_bot_token', newToken)

        // Обновляем refresh токен, если сервер вернул новый
        if (response.data.refresh_token) {
          localStorage.setItem('parcel_bot_refresh_token', response.data.refresh_token)
        }

        // Повторяем оригинальный запрос с новым токеном
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        processQueue(null, newToken)
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh не удался — очищаем авторизацию и редиректим
        localStorage.removeItem('parcel_bot_token')
        localStorage.removeItem('parcel_bot_refresh_token')
        processQueue(refreshError, null)
        window.location.href = '/'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default api
