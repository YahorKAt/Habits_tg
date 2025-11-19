/**
 * API утилиты для работы с бэкендом
 */

import { apiCache } from './apiCache.js'

const API_URL = import.meta.env.VITE_API_URL

// Кэш для getClientLocalTime (вычисляется только раз в 10 секунд)
let cachedClientTime = null
let cachedTime = 0

/**
 * Получает локальное время клиента с timezone offset (кэшируется на 5 секунд)
 */
export const getClientLocalTime = () => {
  const now = Date.now()
  if (cachedClientTime && now - cachedTime < 10000) {
    return cachedClientTime
  }

  const date = new Date()
  const timezoneOffset = -date.getTimezoneOffset() // минуты от UTC (инвертируем знак)
  const offsetHours = Math.floor(Math.abs(timezoneOffset) / 60)
  const offsetMinutes = Math.abs(timezoneOffset) % 60
  const offsetSign = timezoneOffset >= 0 ? '+' : '-'
  const offsetString = `${offsetSign}${String(offsetHours).padStart(2, '0')}:${String(offsetMinutes).padStart(2, '0')}`
  cachedClientTime = date.toISOString().slice(0, -1) + offsetString
  cachedTime = now
  return cachedClientTime
}

/**
 * Создает API клиент с автоматической добавкой заголовков и кэшированием
 */
export const createApiClient = (initData) => {
  return async (path, options = {}) => {
    // Для GET запросов проверяем кэш
    const isGetRequest = !options.method || options.method === 'GET'
    const cacheKey = isGetRequest ? `${path}_${initData?.slice(0, 20)}` : null

    if (isGetRequest && cacheKey) {
      const cached = apiCache.get(cacheKey)
      if (cached) {
        return cached
      }
    }

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

    // Кэшируем только GET запросы
    if (isGetRequest && cacheKey) {
      apiCache.set(cacheKey, data)
    }

    return data
  }
}

/**
 * Инвалидирует кэш по паттерну
 */
export const invalidateCache = (pattern) => {
  apiCache.invalidate(pattern)
}

