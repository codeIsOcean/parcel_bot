/**
 * Разбор параметра запуска — зеркало shared/deeplinks.py.
 * Один параметр (parcel_12, flight_7, publish, admin...) → путь внутри приложения.
 */

// Именованные экраны
const NAMED = {
  publish: '/publish-flight',
  send: '/send',
  requests: '/requests',
  parcels: '/parcels',
  chats: '/chats',
  wallet: '/wallet',
  support: '/support',
  admin: '/admin',
  admin_support: '/admin?tab=support',
  admin_groups: '/admin?tab=groups',
}

// Сущности с числовым id
const ENTITY = {
  parcel: (id) => `/parcels/${id}`,
  flight: (id) => `/flights/${id}`,
  profile: (id) => `/profile/${id}`,
  chat: (id) => `/chats/${id}`,
}

/**
 * Путь для параметра запуска. Неизвестное — главная.
 */
export function screenPath(param) {
  if (!param) return '/'
  if (NAMED[param]) return NAMED[param]
  const match = /^(parcel|flight|profile|chat)_(\d{1,18})$/.exec(param)
  if (match) return ENTITY[match[1]](match[2])
  return '/'
}

/**
 * Куда открыть приложение: ?screen= из адреса важнее start_param.
 */
export function resolveStartScreen(queryScreen, startParam) {
  const raw = (Array.isArray(queryScreen) ? queryScreen[0] : queryScreen) || startParam
  return screenPath(raw)
}
