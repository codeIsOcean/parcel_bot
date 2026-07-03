import api from './client'

/**
 * API для работы с посылками.
 */
export const parcelsApi = {
  /**
   * Получить мои посылки с пагинацией.
   */
  getMyParcels: (params = {}) =>
    api.get('/parcels/my', { params }),

  /**
   * Создать новую посылку (заявку на отправку).
   */
  create: (data) =>
    api.post('/parcels', data),

  /**
   * Получить детали посылки.
   */
  getById: (id) =>
    api.get(`/parcels/${id}`),

  /**
   * Отменить посылку.
   */
  cancel: (id) =>
    api.post(`/parcels/${id}/cancel`),
}
