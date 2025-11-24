/**
 * Хук для операций с задачами
 * Инкапсулирует бизнес-логику работы с задачами
 */

import { useState, useCallback, useRef } from 'react'
import * as taskService from '../services/taskService.js'

/**
 * Хук для управления операциями с задачами
 */
export const useTaskOperations = (apiClient) => {
  const [togglingTasks, setTogglingTasks] = useState(new Set())
  const [deletingTasks, setDeletingTasks] = useState(new Set())
  const [togglingSubtasks, setTogglingSubtasks] = useState(new Set())
  const [deletingSubtasks, setDeletingSubtasks] = useState(new Set())

  const taskUpdateVersionsRef = useRef(new Map())
  const subtaskUpdateVersionsRef = useRef(new Map())

  /**
   * Переключает статус выполнения задачи
   */
  const toggleTask = useCallback(async (task, isPastDate, onTaskUpdate) => {
    if (togglingTasks.has(task.id)) return
    if (isPastDate) return

    setTogglingTasks(prev => new Set(prev).add(task.id))
    const updateVersion = Date.now()
    taskUpdateVersionsRef.current.set(task.id, updateVersion)

    const newCompletedState = !task.completed

    try {
      const updated = await taskService.toggleTaskCompletion(apiClient, task.id)

      const currentVersion = taskUpdateVersionsRef.current.get(task.id)
      if (currentVersion !== updateVersion) return

      // Если задача отменяется, отменяем все подзадачи
      if (!updated.completed && task.subtasks?.length > 0) {
        const uncompletedSubtasks = task.subtasks.map(async (subtask) => {
          if (subtask.completed) {
            try {
              return await taskService.toggleSubtaskCompletion(apiClient, subtask.id)
            } catch (error) {
              console.error(`Error uncompleting subtask ${subtask.id}:`, error)
              return subtask
            }
          }
          return subtask
        })

        Promise.all(uncompletedSubtasks).then(updatedSubtasks => {
          const latestVersion = taskUpdateVersionsRef.current.get(task.id)
          if (latestVersion === updateVersion) {
            onTaskUpdate({ ...updated, subtasks: updatedSubtasks })
          }
        })
      } else {
        onTaskUpdate(updated)
      }
    } catch (error) {
      console.error('Error toggling task:', error)
      const currentVersion = taskUpdateVersionsRef.current.get(task.id)
      if (currentVersion === updateVersion) {
        onTaskUpdate({ ...task, completed: !newCompletedState })
      }
    } finally {
      setTogglingTasks(prev => {
        const next = new Set(prev)
        next.delete(task.id)
        return next
      })
    }
  }, [apiClient, togglingTasks])

  /**
   * Удаляет задачу
   */
  const deleteTask = useCallback(async (task, isPastDate, onTaskDelete) => {
    if (deletingTasks.has(task.id)) return
    if (isPastDate) return

    setDeletingTasks(prev => new Set(prev).add(task.id))

    try {
      await taskService.deleteTask(apiClient, task.id)
      onTaskDelete(task.id)
    } catch (error) {
      console.error('Error deleting task:', error)
    } finally {
      setDeletingTasks(prev => {
        const next = new Set(prev)
        next.delete(task.id)
        return next
      })
    }
  }, [apiClient, deletingTasks])

  /**
   * Переключает статус выполнения подзадачи
   */
  const toggleSubtask = useCallback(async (subtask, parentTask, isPastDate, onSubtaskUpdate) => {
    if (togglingSubtasks.has(subtask.id)) return
    if (isPastDate) return

    setTogglingSubtasks(prev => new Set(prev).add(subtask.id))
    const updateVersion = Date.now()
    subtaskUpdateVersionsRef.current.set(subtask.id, updateVersion)

    try {
      const updated = await taskService.toggleSubtaskCompletion(apiClient, subtask.id)

      const currentVersion = subtaskUpdateVersionsRef.current.get(subtask.id)
      if (currentVersion !== updateVersion) return

      onSubtaskUpdate(updated, parentTask.id)

      // Если все подзадачи выполнены, автоматически отмечаем задачу
      // Если хотя бы одна не выполнена, отменяем задачу
      // Эта логика обрабатывается в компоненте
    } catch (error) {
      console.error('Error toggling subtask:', error)
      const currentVersion = subtaskUpdateVersionsRef.current.get(subtask.id)
      if (currentVersion === updateVersion) {
        onSubtaskUpdate({ ...subtask, completed: !subtask.completed }, parentTask.id)
      }
    } finally {
      setTogglingSubtasks(prev => {
        const next = new Set(prev)
        next.delete(subtask.id)
        return next
      })
    }
  }, [apiClient, togglingSubtasks])

  /**
   * Удаляет подзадачу
   */
  const deleteSubtask = useCallback(async (subtaskId, parentTaskId, isPastDate, onSubtaskDelete) => {
    if (deletingSubtasks.has(subtaskId)) return
    if (isPastDate) return

    setDeletingSubtasks(prev => new Set(prev).add(subtaskId))

    try {
      await taskService.deleteSubtask(apiClient, subtaskId)
      onSubtaskDelete(subtaskId, parentTaskId)
    } catch (error) {
      console.error('Error deleting subtask:', error)
    } finally {
      setDeletingSubtasks(prev => {
        const next = new Set(prev)
        next.delete(subtaskId)
        return next
      })
    }
  }, [apiClient, deletingSubtasks])

  return {
    toggleTask,
    deleteTask,
    toggleSubtask,
    deleteSubtask,
    togglingTasks,
    deletingTasks,
    togglingSubtasks,
    deletingSubtasks,
  }
}

