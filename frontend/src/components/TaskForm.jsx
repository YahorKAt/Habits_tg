/**
 * Компонент формы для создания/редактирования задачи
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { createApiClient } from '../utils/api.js'
import { useInitData } from '../hooks/useTelegram.js'
import { TASK_CATEGORIES, FREQUENCY_OPTIONS } from '../constants/index.js'
import * as taskService from '../services/taskService.js'

/**
 * Компонент формы задачи
 * @param {Function} onBack - функция возврата назад
 * @param {Function} onTaskCreated - функция обратного вызова после создания/обновления
 * @param {Object} task - задача для редактирования (null для создания новой)
 */
export default function TaskForm({ onBack, onTaskCreated, task = null }) {
  const initData = useInitData()
  const isEditing = task !== null
  
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('personal')
  const [frequency, setFrequency] = useState('daily')
  const [loading, setLoading] = useState(false)

  const apiClient = useMemo(() => createApiClient(initData), [initData])

  // Инициализация полей при редактировании
  useEffect(() => {
    if (isEditing && task) {
      setTitle(task.title || '')
      setDescription(task.description || '')
      setCategory(task.category || 'personal')
      setFrequency(task.frequency || 'daily')
    } else {
      setTitle('')
      setDescription('')
      setCategory('personal')
      setFrequency('daily')
    }
  }, [isEditing, task])

  const handleSubmit = useCallback(async () => {
    if (loading) return
    if (!title.trim()) return

    setLoading(true)
    try {
      const taskData = {
        title,
        description,
        category,
        frequency,
      }

      let result
      if (isEditing) {
        result = await taskService.updateTask(apiClient, task.id, taskData)
        onTaskCreated(result, true)
      } else {
        result = await taskService.createTask(apiClient, taskData)
        onTaskCreated(result, false)
      }
    } catch (error) {
      console.error(`Error ${isEditing ? 'updating' : 'creating'} task:`, error)
      alert(`Ошибка при ${isEditing ? 'обновлении' : 'создании'} задачи`)
    } finally {
      setLoading(false)
    }
  }, [apiClient, title, description, category, frequency, isEditing, task, onTaskCreated, loading])

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
          <h1 className="text-xl font-semibold">{isEditing ? 'Редактировать задачу' : 'Новая задача'}</h1>
        </div>
      </div>

      <div className="p-4 space-y-6 pb-28">
        {/* Название задачи */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Название задачи</label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="input"
            placeholder="Введите название задачи"
          />
        </div>

        {/* Описание */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Описание</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            className="input resize-none"
            rows={4}
            placeholder="Добавьте описание (необязательно)"
          />
        </div>

        {/* Категория */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Категория</label>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(TASK_CATEGORIES).map(([key, cat]) => (
              <button
                key={key}
                onClick={() => setCategory(key)}
                className={`p-4 rounded-xl border-2 transition-colors ${
                  category === key
                    ? 'border-orange-500 bg-orange-50'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className="text-2xl mb-1">{cat.icon}</div>
                <div className="text-sm font-medium">{cat.name}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Частота */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Частота выполнения</label>
          <div className="space-y-2">
            {FREQUENCY_OPTIONS.map(option => (
              <button
                key={option.value}
                onClick={() => setFrequency(option.value)}
                className={`w-full p-4 rounded-xl border-2 text-left transition-colors ${
                  frequency === option.value
                    ? 'border-orange-500 bg-orange-50'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className="font-medium">{option.label}</div>
                <div className="text-sm text-gray-500 mt-1">{option.description}</div>
              </button>
            ))}
          </div>
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
            {loading ? (isEditing ? 'Сохранение...' : 'Создание...') : (isEditing ? 'Сохранить изменения' : 'Создать задачу')}
          </button>
        </div>
      </div>
    </div>
  )
}

