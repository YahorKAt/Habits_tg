/**
 * Утилиты для работы с датами
 */
import { format, startOfWeek, addDays, isSameDay, isToday, startOfMonth, endOfMonth, eachDayOfInterval, getDay, isPast, startOfDay } from 'date-fns'
import { ru } from 'date-fns/locale'

/**
 * Форматирует дату для отображения
 */
export const formatDate = (date, formatStr = 'dd MMMM yyyy') => {
  return format(date, formatStr, { locale: ru })
}

/**
 * Проверяет, является ли дата прошлой
 */
export const isPastDate = (date) => {
  return isPast(startOfDay(date))
}

/**
 * Получает массив дней вокруг указанной даты
 */
export const getDaysAround = (centerDate, daysBefore = 30, daysAfter = 0) => {
  const days = []
  const today = new Date()

  for (let i = daysBefore; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    days.push(d)
  }

  for (let i = 1; i <= daysAfter; i++) {
    const d = new Date(today)
    d.setDate(today.getDate() + i)
    days.push(d)
  }

  return days
}

/**
 * Форматирует дату для API запроса (YYYY-MM-DD)
 */
export const formatDateForAPI = (date) => {
  return format(date, 'yyyy-MM-dd')
}

