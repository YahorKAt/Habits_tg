/**
 * API утилиты для работы с бэкендом
 */

const API_URL = import.meta.env.VITE_API_URL

/**
 * Получает локальное время клиента с timezone offset
 */
export const getClientLocalTime = () => {
  const date = new Date()
  const timezoneOffset = -date.getTimezoneOffset() // минуты от UTC (инвертируем знак)
  const offsetHours = Math.floor(Math.abs(timezoneOffset) / 60)
  const offsetMinutes = Math.abs(timezoneOffset) % 60
  const offsetSign = timezoneOffset >= 0 ? '+' : '-'
  const offsetString = `${offsetSign}${String(offsetHours).padStart(2, '0')}:${String(offsetMinutes).padStart(2, '0')}`
  return date.toISOString().slice(0, -1) + offsetString
}

/**
 * Создает API клиент с автоматической добавкой заголовков
 */
export const createApiClient = (initData) => {
  return async (path, options = {}) => {
    const clientTime = getClientLocalTime()
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData,
        'X-Client-Time': clientTime,
        ...(options.headers || {})
      }
    })
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    return data
  }
}

