/**
 * Хук для операций с заметками
 * Инкапсулирует бизнес-логику работы с заметками
 */

import { useState, useCallback } from 'react'
import * as noteService from '../services/noteService.js'

/**
 * Хук для управления операциями с заметками
 */
export const useNoteOperations = (apiClient) => {
  const [isCreating, setIsCreating] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  /**
   * Создает новую заметку
   */
  const createNote = useCallback(async (noteData, onSuccess) => {
    if (isCreating) {
      console.log('⏸️  [useNoteOperations] Создание заметки уже выполняется, пропуск')
      return
    }

    console.log('📝 [useNoteOperations] Создание заметки для даты:', noteData.date)
    setIsCreating(true)
    try {
      const created = await noteService.createNote(apiClient, noteData)
      onSuccess(created)
      console.log('✅ [useNoteOperations] Заметка успешно создана:', created.id)
    } catch (error) {
      console.error('❌ [useNoteOperations] Ошибка создания заметки:', error)
      throw error
    } finally {
      setIsCreating(false)
    }
  }, [apiClient, isCreating])

  /**
   * Обновляет существующую заметку
   */
  const updateNote = useCallback(async (noteId, noteData, onSuccess) => {
    if (isSaving) {
      console.log('⏸️  [useNoteOperations] Обновление заметки уже выполняется, пропуск')
      return
    }

    console.log(`✏️  [useNoteOperations] Обновление заметки ${noteId}`)
    setIsSaving(true)
    try {
      const updated = await noteService.updateNote(apiClient, noteId, noteData)
      onSuccess(updated)
      console.log(`✅ [useNoteOperations] Заметка ${noteId} успешно обновлена`)
    } catch (error) {
      console.error(`❌ [useNoteOperations] Ошибка обновления заметки ${noteId}:`, error)
      throw error
    } finally {
      setIsSaving(false)
    }
  }, [apiClient, isSaving])

  /**
   * Удаляет заметку
   */
  const deleteNote = useCallback(async (noteId, onSuccess) => {
    console.log(`🗑️  [useNoteOperations] Удаление заметки ${noteId}`)
    try {
      await noteService.deleteNote(apiClient, noteId)
      onSuccess(noteId)
      console.log(`✅ [useNoteOperations] Заметка ${noteId} успешно удалена`)
    } catch (error) {
      console.error(`❌ [useNoteOperations] Ошибка удаления заметки ${noteId}:`, error)
      throw error
    }
  }, [apiClient])

  return {
    createNote,
    updateNote,
    deleteNote,
    isCreating,
    isSaving,
  }
}

