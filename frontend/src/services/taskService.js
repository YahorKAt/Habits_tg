/**
 * Сервис для работы с задачами
 * Отвечает за все API запросы, связанные с задачами
 */

import { formatDateForAPI } from '../utils/dateUtils.js'

/**
 * Создает новую задачу
 */
export const createTask = async (apiClient, taskData) => {
  return await apiClient('/task', {
    method: 'POST',
    body: JSON.stringify({
      title: taskData.title.trim(),
      description: taskData.description.trim(),
      category: taskData.category,
      frequency: taskData.frequency,
    })
  })
}

/**
 * Обновляет существующую задачу
 */
export const updateTask = async (apiClient, taskId, taskData) => {
  return await apiClient(`/task/${taskId}`, {
    method: 'PUT',
    body: JSON.stringify({
      title: taskData.title.trim(),
      description: taskData.description.trim(),
      category: taskData.category,
      frequency: taskData.frequency,
    })
  })
}

/**
 * Удаляет задачу
 */
export const deleteTask = async (apiClient, taskId) => {
  return await apiClient(`/task/${taskId}`, { method: 'DELETE' })
}

/**
 * Получает список задач на дату
 */
export const getTasksByDate = async (apiClient, date) => {
  const dateStr = formatDateForAPI(date)
  return await apiClient(`/tasks?date=${dateStr}`)
}

/**
 * Переключает статус выполнения задачи
 */
export const toggleTaskCompletion = async (apiClient, taskId) => {
  return await apiClient(`/task/${taskId}/complete`, { method: 'POST' })
}

/**
 * Создает новую подзадачу
 */
export const createSubtask = async (apiClient, parentTaskId, title) => {
  return await apiClient('/subtask', {
    method: 'POST',
    body: JSON.stringify({
      task_id: parentTaskId,
      title: title.trim(),
    })
  })
}

/**
 * Обновляет подзадачу
 */
export const updateSubtask = async (apiClient, subtaskId, title) => {
  return await apiClient(`/subtask/${subtaskId}`, {
    method: 'PUT',
    body: JSON.stringify({
      title: title.trim(),
    })
  })
}

/**
 * Удаляет подзадачу
 */
export const deleteSubtask = async (apiClient, subtaskId) => {
  return await apiClient(`/subtask/${subtaskId}`, { method: 'DELETE' })
}

/**
 * Переключает статус выполнения подзадачи
 */
export const toggleSubtaskCompletion = async (apiClient, subtaskId) => {
  return await apiClient(`/subtask/${subtaskId}/complete`, { method: 'POST' })
}

