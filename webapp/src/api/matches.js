import api from './client'

/**
 * API заявок на перевозку (связь посылка ↔ рейс).
 */
export const matchesApi = {
  /**
   * Входящие заявки по всем моим активным рейсам.
   * Заявки приходят всегда, право ответить — в поле access каждой группы.
   */
  getIncoming: () =>
    api.get('/matches/incoming'),

  /**
   * Заявки на конкретный рейс.
   */
  getByFlight: (flightId, params = {}) =>
    api.get(`/matches/flight/${flightId}`, { params }),

  /**
   * Создать заявку — откликнуться посылкой на рейс.
   */
  create: (parcelId, flightId) =>
    api.post('/matches', { parcel_id: parcelId, flight_id: flightId }),

  /**
   * Принять заявку. Вернёт 402, если публикация рейса не оплачена.
   */
  accept: (matchId) =>
    api.post(`/matches/${matchId}/accept`),

  /**
   * Отклонить заявку.
   */
  decline: (matchId) =>
    api.post(`/matches/${matchId}/decline`),
}
