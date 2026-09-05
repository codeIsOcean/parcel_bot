import api from './client'

/**
 * API кабинета: баланс в звёздах и пополнение.
 */
export const walletApi = {
  /**
   * Баланс, цены и история операций.
   */
  get: () =>
    api.get('/wallet'),

  /**
   * Открыть сегодняшний рабочий день перевозчика.
   * Списывает дневной тариф, если день ещё не открыт.
   */
  openDay: () =>
    api.post('/wallet/day'),

  /**
   * Ссылка на счёт Telegram Stars.
   */
  topUpStars: (amountStars) =>
    api.post('/wallet/topup/stars', { amount_stars: amountStars }),

  /**
   * Реквизиты перевода в TON.
   */
  topUpTon: (amountStars) =>
    api.post('/wallet/topup/ton', { amount_stars: amountStars }),

  /**
   * Проверить, дошёл ли перевод в TON.
   */
  checkTon: (paymentId) =>
    api.get(`/wallet/topup/ton/${paymentId}`),
}
