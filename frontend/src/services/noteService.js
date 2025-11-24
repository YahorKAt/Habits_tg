/**
 * Сервис для работы с заметками
 * Отвечает за все API запросы, связанные с заметками
 */

import { formatDateForAPI } from '../utils/dateUtils.js'

/**
 * Получает заметки на конкретную дату
 */
export const getNotesByDate = async (apiClient, date) => {
  const dateStr = formatDateForAPI(date)
  return await apiClient(`/notes?date=${dateStr}`)
}

/**
 * Получает заметки за месяц
 */
export const getNotesByMonth = async (apiClient, year, month) => {
  return await apiClient(`/notes?year=${year}&month=${month}`)
}

/**
 * Создает новую заметку
 */
export const createNote = async (apiClient, noteData) => {
  return await apiClient('/notes', {
    method: 'POST',
    body: JSON.stringify({
      content: noteData.content.trim(),
      date: noteData.date,
      mood: noteData.mood
    })
  })
}

/**
 * Обновляет существующую заметку
 */
export const updateNote = async (apiClient, noteId, noteData) => {
  return await apiClient(`/notes/${noteId}`, {
    method: 'PUT',
    body: JSON.stringify({
      content: noteData.content.trim(),
      date: noteData.date,
      mood: noteData.mood
    })
  })
}

/**
 * Удаляет заметку
 */
export const deleteNote = async (apiClient, noteId) => {
  return await apiClient(`/notes/${noteId}`, { method: 'DELETE' })
}

