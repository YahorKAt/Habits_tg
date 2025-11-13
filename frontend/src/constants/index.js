/**
 * Константы приложения
 */

// Константы для категорий задач
export const TASK_CATEGORIES = {
  sport: { name: 'Спорт', icon: '🏆', color: '#EF4444' },
  study: { name: 'Учёба', icon: '🎓', color: '#3B82F6' },
  work: { name: 'Работа', icon: '💼', color: '#10B981' },
  personal: { name: 'Личное', icon: '👤', color: '#8B5CF6' },
}

export const FREQUENCY_OPTIONS = [
  { value: 'daily', label: 'Ежедневно', description: 'Выполняется каждый день' },
  { value: 'weekly', label: 'Еженедельно', description: 'Выполняется раз в неделю' },
  { value: 'monthly', label: 'Ежемесячно', description: 'Выполняется раз в месяц' },
]

// Варианты настроения для заметок
export const MOOD_OPTIONS = [
  { value: 'very_bad', label: 'Агрессивное' },
  { value: 'bad', label: 'Плохое' },
  { value: 'neutral', label: 'Нормальное' },
  { value: 'good', label: 'Хорошее' },
  { value: 'very_good', label: 'Отличное' }
]

