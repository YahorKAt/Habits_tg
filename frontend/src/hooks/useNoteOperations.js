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
    if (isCreating) return

    setIsCreating(true)
    try {
      const created = await noteService.createNote(apiClient, noteData)
      onSuccess(created)
    } catch (error) {
      console.error('Error creating note:', error)
      throw error
    } finally {
      setIsCreating(false)
    }
  }, [apiClient, isCreating])

  /**
   * Обновляет существующую заметку
   */
  const updateNote = useCallback(async (noteId, noteData, onSuccess) => {
    if (isSaving) return

    setIsSaving(true)
    try {
      const updated = await noteService.updateNote(apiClient, noteId, noteData)
      onSuccess(updated)
    } catch (error) {
      console.error('Error updating note:', error)
      throw error
    } finally {
      setIsSaving(false)
    }
  }, [apiClient, isSaving])

  /**
   * Удаляет заметку
   */
  const deleteNote = useCallback(async (noteId, onSuccess) => {
    try {
      await noteService.deleteNote(apiClient, noteId)
      onSuccess(noteId)
    } catch (error) {
      console.error('Error deleting note:', error)
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

