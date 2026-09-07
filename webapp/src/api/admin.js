import api from './client'

/**
 * API админ-панели: /api/v1/admin/*.
 * Interceptor клиента уже разворачивает response.data.
 */
export const adminApi = {
  // Проверка доступа — панель открывается только после 200
  me: () => api.get('/admin/me'),

  // Сводка по сервису
  stats: () => api.get('/admin/stats'),

  // Пользователи: поиск, фильтр, пагинация
  users: (params = {}) => api.get('/admin/users', { params }),
  // Карточка пользователя с посылками, рейсами и жалобами
  user: (id) => api.get(`/admin/users/${id}`),
  // Заблокировать (value=true) / разблокировать
  block: (id, value) => api.post(`/admin/users/${id}/block`, { value }),
  // Галочка проверенного
  verify: (id, value) => api.post(`/admin/users/${id}/verify`, { value }),
  // Назначить / снять администратора
  setAdmin: (id, value) => api.post(`/admin/users/${id}/admin`, { value }),
  // Ручное изменение баланса
  balance: (id, data) => api.post(`/admin/users/${id}/balance`, data),

  // Посылки
  parcels: (params = {}) => api.get('/admin/parcels', { params }),
  cancelParcel: (id) => api.post(`/admin/parcels/${id}/cancel`),

  // Рейсы
  flights: (params = {}) => api.get('/admin/flights', { params }),
  cancelFlight: (id) => api.post(`/admin/flights/${id}/cancel`),

  // Жалобы
  reports: (status = 'open') => api.get('/admin/reports', { params: { status } }),
  resolveReport: (id, status) => api.post(`/admin/reports/${id}/resolve`, { status }),

  // Платежи
  payments: (params = {}) => api.get('/admin/payments', { params }),

  // Рассылка
  broadcast: (data) => api.post('/admin/broadcast', data),

  // Группы для кросс-постинга
  groups: () => api.get('/admin/groups'),
  addGroup: (link) => api.post('/admin/groups', { link }),
  updateGroup: (id, data) => api.patch(`/admin/groups/${id}`, data),
  deleteGroup: (id) => api.delete(`/admin/groups/${id}`),

  // Поддержка
  supportSessions: (status = 'open') => api.get('/admin/support/sessions', { params: { status } }),
  supportMessages: (userId) => api.get(`/admin/support/${userId}/messages`),
  supportReply: (userId, text) => api.post(`/admin/support/${userId}/reply`, { text }),
  supportClose: (userId) => api.post(`/admin/support/${userId}/close`),
}
