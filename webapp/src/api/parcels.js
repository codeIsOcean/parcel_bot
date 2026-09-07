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

  /**
   * Отслеживание: этапы, код выдачи и доступные действия.
   */
  getTracking: (id) =>
    api.get(`/parcels/${id}/tracking`),

  /**
   * Перевозчик забрал посылку у отправителя.
   */
  markHanded: (id, photoFileIds = null) =>
    api.post(`/parcels/${id}/handed`, { photo_file_ids: photoFileIds }),

  /**
   * Перевозчик вылетел.
   */
  markInTransit: (id) =>
    api.post(`/parcels/${id}/transit`),

  /**
   * Перевозчик прилетел.
   */
  markArrived: (id) =>
    api.post(`/parcels/${id}/arrived`),

  /**
   * Перевозчик закрывает доставку кодом получателя.
   */
  markDelivered: (id, code, photoFileIds = null) =>
    api.post(`/parcels/${id}/delivered`, { code, photo_file_ids: photoFileIds }),

  /**
   * Перевозчик откликается на посылку своим рейсом.
   */
  offer: (id, flightId) =>
    api.post(`/parcels/${id}/offer`, { flight_id: flightId }),

  /**
   * Отклики и заявки по посылке.
   */
  getOffers: (id) =>
    api.get(`/parcels/${id}/offers`),
}
