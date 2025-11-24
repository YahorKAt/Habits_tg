/**
 * Сервис для работы со статистикой
 * Отвечает за все API запросы, связанные со статистикой
 */

/**
 * Получает статистику за период
 */
export const getStatistics = async (apiClient, period) => {
  console.log(`📊 [StatisticsService] Загрузка статистики за период: ${period}`)
  const result = await apiClient(`/stats?period=${period}`)
  console.log(`✅ [StatisticsService] Статистика загружена:`, result)
  return result
}

/**
 * Получает статистику по привычкам
 */
export const getHabitsStatistics = async (apiClient) => {
  console.log(`📊 [StatisticsService] Загрузка статистики по привычкам`)
  const result = await apiClient('/habits')
  console.log(`✅ [StatisticsService] Статистика по привычкам загружена:`, result.length, 'привычек')
  return result
}

