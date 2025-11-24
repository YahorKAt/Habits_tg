/**
 * Сервис для работы с задачами
 * Отвечает за все API запросы, связанные с задачами
 */

import { formatDateForAPI } from '../utils/dateUtils.js'

/**
 * Создает новую задачу
 */
export const createTask = async (apiClient, taskData) => {
  console.log('📝 [TaskService] Создание задачи:', { title: taskData.title, category: taskData.category, frequency: taskData.frequency })
  const result = await apiClient('/task', {
    method: 'POST',
    body: JSON.stringify({
      title: taskData.title.trim(),
      description: taskData.description.trim(),
      category: taskData.category,
      frequency: taskData.frequency,
    })
  })
  console.log('✅ [TaskService] Задача создана:', result.id)
  return result
}

/**
 * Обновляет существующую задачу
 */
export const updateTask = async (apiClient, taskId, taskData) => {
  console.log(`✏️  [TaskService] Обновление задачи ${taskId}:`, { title: taskData.title, category: taskData.category })
  const result = await apiClient(`/task/${taskId}`, {
    method: 'PUT',
    body: JSON.stringify({
      title: taskData.title.trim(),
      description: taskData.description.trim(),
      category: taskData.category,
      frequency: taskData.frequency,
    })
  })
  console.log(`✅ [TaskService] Задача ${taskId} обновлена`)
  return result
}

/**
 * Удаляет задачу
 */
export const deleteTask = async (apiClient, taskId) => {
  console.log(`🗑️  [TaskService] Удаление задачи ${taskId}`)
  const result = await apiClient(`/task/${taskId}`, { method: 'DELETE' })
  console.log(`✅ [TaskService] Задача ${taskId} удалена`)
  return result
}

/**
 * Получает список задач на дату
 */
export const getTasksByDate = async (apiClient, date) => {
  const dateStr = formatDateForAPI(date)
  console.log(`📋 [TaskService] Загрузка задач на дату: ${dateStr}`)
  const result = await apiClient(`/tasks?date=${dateStr}`)
  console.log(`✅ [TaskService] Загружено ${result.length} задач`)
  return result
}

/**
 * Переключает статус выполнения задачи
 */
export const toggleTaskCompletion = async (apiClient, taskId) => {
  console.log(`✅ [TaskService] Переключение статуса задачи ${taskId}`)
  const result = await apiClient(`/task/${taskId}/complete`, { method: 'POST' })
  console.log(`✅ [TaskService] Статус задачи ${taskId} изменен на ${result.completed ? 'выполнено' : 'не выполнено'}`)
  return result
}

/**
 * Создает новую подзадачу
 */
export const createSubtask = async (apiClient, parentTaskId, title) => {
  console.log(`📝 [TaskService] Создание подзадачи для задачи ${parentTaskId}:`, title)
  const result = await apiClient('/subtask', {
    method: 'POST',
    body: JSON.stringify({
      task_id: parentTaskId,
      title: title.trim(),
    })
  })
  console.log(`✅ [TaskService] Подзадача ${result.id} создана`)
  return result
}

/**
 * Обновляет подзадачу
 */
export const updateSubtask = async (apiClient, subtaskId, title) => {
  console.log(`✏️  [TaskService] Обновление подзадачи ${subtaskId}:`, title)
  const result = await apiClient(`/subtask/${subtaskId}`, {
    method: 'PUT',
    body: JSON.stringify({
      title: title.trim(),
    })
  })
  console.log(`✅ [TaskService] Подзадача ${subtaskId} обновлена`)
  return result
}

/**
 * Удаляет подзадачу
 */
export const deleteSubtask = async (apiClient, subtaskId) => {
  console.log(`🗑️  [TaskService] Удаление подзадачи ${subtaskId}`)
  const result = await apiClient(`/subtask/${subtaskId}`, { method: 'DELETE' })
  console.log(`✅ [TaskService] Подзадача ${subtaskId} удалена`)
  return result
}

/**
 * Переключает статус выполнения подзадачи
 */
export const toggleSubtaskCompletion = async (apiClient, subtaskId) => {
  console.log(`✅ [TaskService] Переключение статуса подзадачи ${subtaskId}`)
  const result = await apiClient(`/subtask/${subtaskId}/complete`, { method: 'POST' })
  console.log(`✅ [TaskService] Статус подзадачи ${subtaskId} изменен на ${result.completed ? 'выполнено' : 'не выполнено'}`)
  return result
}

