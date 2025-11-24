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
  console.log(`📋 [NoteService] Загрузка заметок на дату: ${dateStr}`)
  const result = await apiClient(`/notes?date=${dateStr}`)
  console.log(`✅ [NoteService] Загружено ${result.length} заметок`)
  return result
}

/**
 * Получает заметки за месяц
 */
export const getNotesByMonth = async (apiClient, year, month) => {
  console.log(`📋 [NoteService] Загрузка заметок за месяц: ${year}-${month}`)
  const result = await apiClient(`/notes?year=${year}&month=${month}`)
  console.log(`✅ [NoteService] Загружено ${result.length} заметок за месяц`)
  return result
}

/**
 * Создает новую заметку
 */
export const createNote = async (apiClient, noteData) => {
  console.log(`📝 [NoteService] Создание заметки для даты ${noteData.date}, настроение: ${noteData.mood}`)
  const result = await apiClient('/notes', {
    method: 'POST',
    body: JSON.stringify({
      content: noteData.content.trim(),
      date: noteData.date,
      mood: noteData.mood
    })
  })
  console.log(`✅ [NoteService] Заметка ${result.id} создана`)
  return result
}

/**
 * Обновляет существующую заметку
 */
export const updateNote = async (apiClient, noteId, noteData) => {
  console.log(`✏️  [NoteService] Обновление заметки ${noteId}`)
  const result = await apiClient(`/notes/${noteId}`, {
    method: 'PUT',
    body: JSON.stringify({
      content: noteData.content.trim(),
      date: noteData.date,
      mood: noteData.mood
    })
  })
  console.log(`✅ [NoteService] Заметка ${noteId} обновлена`)
  return result
}

/**
 * Удаляет заметку
 */
export const deleteNote = async (apiClient, noteId) => {
  console.log(`🗑️  [NoteService] Удаление заметки ${noteId}`)
  const result = await apiClient(`/notes/${noteId}`, { method: 'DELETE' })
  console.log(`✅ [NoteService] Заметка ${noteId} удалена`)
  return result
}

