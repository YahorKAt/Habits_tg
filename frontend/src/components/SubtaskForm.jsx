/**
 * Компонент формы для создания/редактирования подзадачи
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { createApiClient } from '../utils/api.js'
import { useInitData } from '../hooks/useTelegram.js'
import { TASK_CATEGORIES } from '../constants/index.js'
import * as taskService from '../services/taskService.js'

/**
 * Компонент формы подзадачи
 * @param {Function} onBack - функция возврата назад
 * @param {Function} onSubtaskCreated - функция обратного вызова после создания/обновления
 * @param {Object} parentTask - родительская задача
 * @param {Object} subtask - подзадача для редактирования (null для создания новой)
 */
export default function SubtaskForm({ onBack, onSubtaskCreated, parentTask, subtask = null }) {
  const initData = useInitData()
  const isEditing = subtask !== null
  
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)

  const apiClient = useMemo(() => createApiClient(initData), [initData])

  useEffect(() => {
    if (isEditing && subtask) {
      setTitle(subtask.title || '')
    } else {
      setTitle('')
    }
  }, [isEditing, subtask])

  const handleSubmit = useCallback(async () => {
    if (loading) return
    if (!title.trim()) return

    setLoading(true)
    try {
      if (isEditing) {
        await taskService.updateSubtask(apiClient, subtask.id, title)
      } else {
        await taskService.createSubtask(apiClient, parentTask.id, title)
      }
      onSubtaskCreated()
    } catch (error) {
      console.error(`Error ${isEditing ? 'updating' : 'creating'} subtask:`, error)
      alert(`Ошибка при ${isEditing ? 'обновлении' : 'создании'} подзадачи`)
    } finally {
      setLoading(false)
    }
  }, [apiClient, title, isEditing, subtask, parentTask, onSubtaskCreated, loading])

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      {/* Header */}
      <div className="bg-white px-4 py-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="text-gray-600">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <h1 className="text-xl font-semibold">{isEditing ? 'Редактировать подзадачу' : 'Новая подзадача'}</h1>
        </div>
        <p className="text-gray-600 text-sm mt-1">
          Для задачи: {parentTask?.title}
        </p>
      </div>

      <div className="p-4 space-y-6 pb-28">
        {/* Информация о родительской задаче */}
        <div className="card bg-gray-50">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{TASK_CATEGORIES[parentTask?.category]?.icon || '📋'}</span>
            <div>
              <div className="text-sm font-medium text-gray-700">
                {TASK_CATEGORIES[parentTask?.category]?.name || 'Общее'}
              </div>
              <div className="text-xs text-gray-500">
                Группа автоматически совпадает с основной задачей
              </div>
            </div>
          </div>
        </div>

        {/* Название подзадачи */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Название подзадачи</label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="input"
            placeholder="Введите название подзадачи"
          />
        </div>
      </div>

      {/* Bottom buttons */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 p-4">
        <div className="flex gap-3">
          <button onClick={onBack} className="btn-secondary flex-1">
            Отмена
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim() || loading}
            className="btn flex-1 flex items-center justify-center gap-2"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {loading ? (isEditing ? 'Сохранение...' : 'Создание...') : (isEditing ? 'Сохранить изменения' : 'Создать подзадачу')}
          </button>
        </div>
      </div>
    </div>
  )
}

