/**
 * Простой кэш для API запросов
 */
class ApiCache {
  constructor(ttl = 30000) { // 30 секунд по умолчанию
    this.cache = new Map()
    this.ttl = ttl
  }

  get(key) {
    const item = this.cache.get(key)
    if (!item) return null

    if (Date.now() - item.timestamp > this.ttl) {
      this.cache.delete(key)
      return null
    }

    return item.data
  }

  set(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    })
  }

  clear() {
    this.cache.clear()
  }

  invalidate(pattern) {
    if (typeof pattern === 'string') {
      // Простая проверка на вхождение строки
      for (const key of this.cache.keys()) {
        if (key.includes(pattern)) {
          this.cache.delete(key)
        }
      }
    } else if (pattern instanceof RegExp) {
      for (const key of this.cache.keys()) {
        if (pattern.test(key)) {
          this.cache.delete(key)
        }
      }
    }
  }
}

// Глобальный экземпляр кэша
export const apiCache = new ApiCache(30000) // 30 секунд TTL

