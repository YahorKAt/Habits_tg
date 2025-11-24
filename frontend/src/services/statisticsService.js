/**
 * Сервис для работы со статистикой
 * Отвечает за все API запросы, связанные со статистикой
 */

/**
 * Получает статистику за период
 */
export const getStatistics = async (apiClient, period) => {
  return await apiClient(`/stats?period=${period}`)
}

/**
 * Получает статистику по привычкам
 */
export const getHabitsStatistics = async (apiClient) => {
  return await apiClient('/habits')
}

