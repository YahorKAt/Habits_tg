/**
 * Страница задач
 * Отображает список задач с фильтрацией и календарем
 */

import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { format, isSameDay, startOfDay } from 'date-fns'
import { ru } from 'date-fns/locale'
import { createApiClient } from '../utils/api.js'
import { useInitData } from '../hooks/useTelegram.js'
import { TASK_CATEGORIES } from '../constants/index.js'
import { formatDateForAPI } from '../utils/dateUtils.js'
import * as taskService from '../services/taskService.js'

/**
 * Страница задач
 * @param {Function} onCreateTask - функция создания новой задачи
 * @param {Function} onEditTask - функция редактирования задачи
 * @param {Function} onTaskUpdated - функция обновления задачи
 * @param {Function} onCreateSubtask - функция создания подзадачи
 * @param {Function} onEditSubtask - функция редактирования подзадачи
 */
export default function TasksPage({ onCreateTask, onEditTask, onTaskUpdated, onCreateSubtask, onEditSubtask }) {
  const initData = useInitData()
  const [tasks, setTasks] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [selectedDate, setSelectedDate] = useState(new Date())
  const ribbonRef = useRef(null)
  const [expandedTasks, setExpandedTasks] = useState(new Set())
  const taskUpdateVersionsRef = useRef(new Map())
  const subtaskUpdateVersionsRef = useRef(new Map())
  const [togglingTasks, setTogglingTasks] = useState(new Set())
  const [deletingTasks, setDeletingTasks] = useState(new Set())
  const [togglingSubtasks, setTogglingSubtasks] = useState(new Set())
  const [deletingSubtasks, setDeletingSubtasks] = useState(new Set())

  const api = useMemo(() => createApiClient(initData), [initData])

  const loadTasks = useCallback(async (date = selectedDate) => {
    setLoading(true)
    try {
      const data = await taskService.getTasksByDate(api, date)
      setTasks(data)
    } finally {
      setLoading(false)
    }
  }, [api, selectedDate])

  const loadTasksRef = useRef(null)
  loadTasksRef.current = loadTasks

  useEffect(() => {
    loadTasks(selectedDate)
  }, [selectedDate, loadTasks])

  const updateTaskInList = useCallback((updatedTask) => {
    setTasks(prev => prev.map(t => t.id === updatedTask.id ? updatedTask : t))
  }, [])

  useEffect(() => {
    if (onTaskUpdated) {
      onTaskUpdated((updatedTask) => {
        if (updatedTask) {
          updateTaskInList(updatedTask)
        } else {
          if (loadTasksRef.current) {
            loadTasksRef.current(selectedDate)
          }
        }
      })
    }
  }, [onTaskUpdated, selectedDate, updateTaskInList])

  const handleDateChange = useCallback((date) => {
    setSelectedDate(date)
  }, [])

  const handleFilterChange = useCallback((filter) => {
    setFilter(filter)
  }, [])

  const toggleTaskExpanded = useCallback((taskId) => {
    setExpandedTasks(prev => {
      const newSet = new Set(prev)
      if (newSet.has(taskId)) {
        newSet.delete(taskId)
      } else {
        newSet.add(taskId)
      }
      return newSet
    })
  }, [])

  const tasksForSelectedDay = useMemo(() => {
    const start = new Date(selectedDate)
    start.setHours(0, 0, 0, 0)
    const end = new Date(selectedDate)
    end.setHours(23, 59, 59, 999)
    return tasks.filter(t => {
      const ts = t.created_at ? new Date(t.created_at) : null
      return ts ? ts >= start && ts <= end : true
    })
  }, [tasks, selectedDate])

  const filteredTasks = useMemo(() => {
    const base = tasksForSelectedDay
    switch (filter) {
      case 'active':
        return base.filter(task => !task.completed)
      case 'completed':
        return base.filter(task => task.completed)
      default:
        return base
    }
  }, [tasksForSelectedDay, filter])

  const daysAround = useMemo(() => {
    const days = []
    const today = new Date()
    for (let i = 30; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(today.getDate() - i)
      days.push(d)
    }
    return days
  }, [])

  useEffect(() => {
    if (ribbonRef.current && daysAround.length > 0) {
      const rafId = requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (!ribbonRef.current) return
          const savedScrollPosition = localStorage.getItem('calendarScrollPosition')
          if (savedScrollPosition !== null) {
            ribbonRef.current.scrollLeft = parseInt(savedScrollPosition, 10)
          } else {
            const hasScrolledBefore = localStorage.getItem('calendarHasScrolled')
            if (!hasScrolledBefore) {
              const today = new Date()
              const todayIndex = daysAround.findIndex(d => isSameDay(d, today))
              if (todayIndex !== -1 && ribbonRef.current) {
                const todayButton = ribbonRef.current.children[todayIndex]
                if (todayButton) {
                  const container = ribbonRef.current
                  const buttonLeft = todayButton.offsetLeft
                  const buttonWidth = todayButton.offsetWidth
                  const containerWidth = container.offsetWidth
                  container.scrollLeft = buttonLeft - (containerWidth / 2) + (buttonWidth / 2)
                  localStorage.setItem('calendarScrollPosition', container.scrollLeft.toString())
                  localStorage.setItem('calendarHasScrolled', 'true')
                }
              }
            }
          }
        })
      })
      return () => cancelAnimationFrame(rafId)
    }
  }, [daysAround])

  useEffect(() => {
    const ribbon = ribbonRef.current
    if (!ribbon) return
    const handleScroll = () => {
      localStorage.setItem('calendarScrollPosition', ribbon.scrollLeft.toString())
    }
    ribbon.addEventListener('scroll', handleScroll)
    return () => ribbon.removeEventListener('scroll', handleScroll)
  }, [])

  const isPastDate = useMemo(() => {
    const today = startOfDay(new Date())
    const selected = startOfDay(selectedDate)
    return selected < today
  }, [selectedDate])

  const toggleTask = useCallback(async (task) => {
    if (togglingTasks.has(task.id)) return
    if (isPastDate) return

    setTogglingTasks(prev => new Set(prev).add(task.id))
    const updateVersion = Date.now()
    taskUpdateVersionsRef.current.set(task.id, updateVersion)
    const newCompletedState = !task.completed

    setTasks(prev => prev.map(t => {
      if (t.id === task.id) {
        const currentTask = t
        const updatedTask = { ...currentTask, completed: newCompletedState }
        if (!newCompletedState && currentTask.subtasks && currentTask.subtasks.length > 0) {
          updatedTask.subtasks = (currentTask.subtasks || []).map(st => ({ ...st, completed: false }))
        }
        return updatedTask
      }
      return t
    }))

    try {
      const updated = await taskService.toggleTaskCompletion(api, task.id)
      const currentVersion = taskUpdateVersionsRef.current.get(task.id)
      if (currentVersion !== updateVersion) return

      if (!updated.completed) {
        setTasks(prev => {
          const currentTask = prev.find(t => t.id === task.id)
          if (!currentTask || !currentTask.subtasks || currentTask.subtasks.length === 0) {
            return prev.map(t => t.id === task.id ? { ...updated, subtasks: [] } : t)
          }

          const uncompletedSubtasks = currentTask.subtasks.map(async (subtask) => {
            if (subtask.completed) {
              try {
                return await taskService.toggleSubtaskCompletion(api, subtask.id)
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
              const finalTask = { ...updated, subtasks: updatedSubtasks }
              setTasks(prevTasks => prevTasks.map(t => {
                if (t.id === task.id) {
                  return finalTask
                }
                return t
              }))
            }
          })

          return prev.map(t => t.id === task.id ? { ...updated, subtasks: currentTask.subtasks } : t)
        })
      } else {
        setTasks(prev => prev.map(t => {
          if (t.id === task.id) {
            return { ...updated, subtasks: t.subtasks || [] }
          }
          return t
        }))
      }
    } catch (error) {
      console.error('Error toggling task:', error)
      const currentVersion = taskUpdateVersionsRef.current.get(task.id)
      if (currentVersion === updateVersion) {
        setTasks(prev => prev.map(t => {
          if (t.id === task.id) {
            return { ...t, completed: !newCompletedState }
          }
          return t
        }))
      }
    } finally {
      setTogglingTasks(prev => {
        const next = new Set(prev)
        next.delete(task.id)
        return next
      })
    }
  }, [api, isPastDate, togglingTasks])

  const deleteTask = useCallback(async (task) => {
    if (deletingTasks.has(task.id)) return
    if (isPastDate) return

    setDeletingTasks(prev => new Set(prev).add(task.id))

    try {
      await taskService.deleteTask(api, task.id)
      setTasks(prev => prev.filter(t => t.id !== task.id))
    } catch (error) {
      console.error('Error deleting task:', error)
    } finally {
      setDeletingTasks(prev => {
        const next = new Set(prev)
        next.delete(task.id)
        return next
      })
    }
  }, [api, isPastDate, deletingTasks])

  const toggleExpanded = toggleTaskExpanded

  const toggleSubtask = useCallback(async (subtask, parentTask) => {
    if (togglingSubtasks.has(subtask.id)) return
    if (isPastDate) return

    setTogglingSubtasks(prev => new Set(prev).add(subtask.id))
    const updateVersion = Date.now()
    subtaskUpdateVersionsRef.current.set(subtask.id, updateVersion)

    let newCompletedState = null
    setTasks(prev => {
      const currentParentTask = prev.find(t => t.id === parentTask.id)
      if (!currentParentTask) return prev

      const currentSubtask = (currentParentTask.subtasks || []).find(st => st.id === subtask.id)
      if (!currentSubtask) return prev

      newCompletedState = !currentSubtask.completed

      return prev.map(t => {
        if (t.id === parentTask.id) {
          const updatedSubtasks = (t.subtasks || []).map(st =>
            st.id === subtask.id ? { ...st, completed: newCompletedState } : st
          )

          const allCompleted = updatedSubtasks.length > 0 && updatedSubtasks.every(st => st.completed)
          const updatedTask = { ...t, subtasks: updatedSubtasks }
          if (allCompleted && !t.completed) {
            updatedTask.completed = true
          } else if (!allCompleted && t.completed) {
            updatedTask.completed = false
          }

          return updatedTask
        }
        return t
      })
    })

    if (newCompletedState === null) {
      return
    }

    try {
      const updated = await taskService.toggleSubtaskCompletion(api, subtask.id)
      const currentVersion = subtaskUpdateVersionsRef.current.get(subtask.id)
      if (currentVersion !== updateVersion) return

      setTasks(prev => {
        const currentParentTask = prev.find(t => t.id === parentTask.id)
        if (!currentParentTask) return prev

        return prev.map(t => {
          if (t.id === parentTask.id) {
            const updatedSubtasks = (t.subtasks || []).map(st =>
              st.id === subtask.id ? updated : st
            )

            const updatedTask = { ...t, subtasks: updatedSubtasks }
            const allCompleted = updatedSubtasks.length > 0 && updatedSubtasks.every(st => st.completed)

            if (allCompleted && !t.completed) {
              taskService.toggleTaskCompletion(api, t.id).then(updatedTask => {
                const latestVersion = subtaskUpdateVersionsRef.current.get(subtask.id)
                if (latestVersion === updateVersion) {
                  setTasks(prevTasks => {
                    const currentTask = prevTasks.find(tt => tt.id === updatedTask.id)
                    const finalTask = { ...updatedTask, subtasks: currentTask?.subtasks || updatedSubtasks }
                    return prevTasks.map(task => {
                      if (task.id === updatedTask.id) {
                        return finalTask
                      }
                      return task
                    })
                  })
                }
              }).catch(error => {
                console.error('Error auto-completing task:', error)
              })
            } else if (!allCompleted && t.completed) {
              taskService.toggleTaskCompletion(api, t.id).then(updatedTask => {
                const latestVersion = subtaskUpdateVersionsRef.current.get(subtask.id)
                if (latestVersion === updateVersion) {
                  setTasks(prevTasks => {
                    const currentTask = prevTasks.find(tt => tt.id === updatedTask.id)
                    const finalTask = { ...updatedTask, subtasks: currentTask?.subtasks || updatedSubtasks }
                    return prevTasks.map(task => {
                      if (task.id === updatedTask.id) {
                        return finalTask
                      }
                      return task
                    })
                  })
                }
              }).catch(error => {
                console.error('Error auto-uncompleting task:', error)
              })
            }

            return { ...t, subtasks: updatedSubtasks }
          }
          return t
        })
      })
    } catch (error) {
      console.error('Error toggling subtask:', error)
      const currentVersion = subtaskUpdateVersionsRef.current.get(subtask.id)
      if (currentVersion === updateVersion && newCompletedState !== null) {
        setTasks(prev => prev.map(t => {
          if (t.id === parentTask.id) {
            const updatedSubtasks = (t.subtasks || []).map(st =>
              st.id === subtask.id ? { ...st, completed: !newCompletedState } : st
            )
            const allCompleted = updatedSubtasks.length > 0 && updatedSubtasks.every(st => st.completed)
            return {
              ...t,
              subtasks: updatedSubtasks,
              completed: allCompleted ? t.completed : false
            }
          }
          return t
        }))
      }
    } finally {
      setTogglingSubtasks(prev => {
        const next = new Set(prev)
        next.delete(subtask.id)
        return next
      })
    }
  }, [api, isPastDate, togglingSubtasks])

  const deleteSubtask = useCallback(async (subtaskId, parentTaskId) => {
    if (deletingSubtasks.has(subtaskId)) return
    if (isPastDate) return

    setDeletingSubtasks(prev => new Set(prev).add(subtaskId))

    try {
      await taskService.deleteSubtask(api, subtaskId)
      setTasks(prev => prev.map(t => {
        if (t.id === parentTaskId) {
          const updatedSubtasks = (t.subtasks || []).filter(st => st.id !== subtaskId)
          const allCompleted = updatedSubtasks.length > 0 && updatedSubtasks.every(st => st.completed)

          if (!allCompleted && t.completed) {
            taskService.toggleTaskCompletion(api, t.id).then(updatedTask => {
              setTasks(prevTasks => prevTasks.map(task => {
                if (task.id === updatedTask.id) {
                  return { ...updatedTask, subtasks: updatedSubtasks }
                }
                return task
              }))
            }).catch(error => {
              console.error('Error auto-uncompleting task after subtask deletion:', error)
            })
          }

          return {
            ...t,
            subtasks: updatedSubtasks
          }
        }
        return t
      }))
    } catch (error) {
      console.error('Error deleting subtask:', error)
    } finally {
      setDeletingSubtasks(prev => {
        const next = new Set(prev)
        next.delete(subtaskId)
        return next
      })
    }
  }, [api, isPastDate, deletingSubtasks])

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className="bg-white px-4 py-4">
        <h1 className="text-xl font-semibold">Мои задачи</h1>
        <div className="flex gap-2 mt-4">
          {[
            { key: 'all', label: 'Все' },
            { key: 'active', label: 'Активные' },
            { key: 'completed', label: 'Выполненные' }
          ].map(tab => (
            <button
              key={tab.key}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${filter === tab.key ? 'tab-active' : 'tab-inactive'}`}
              onClick={() => handleFilterChange(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 py-4 pb-24 space-y-3">
        <div className="card mb-2">
          <div className="flex items-center justify-between mb-3">
            <div className="text-base font-semibold">
              {(() => { const label = format(selectedDate, 'd LLLL yyyy', { locale: ru }); return label.charAt(0).toUpperCase() + label.slice(1) })()}
            </div>
          </div>
          <div
            ref={ribbonRef}
            className="flex gap-2 overflow-x-auto pb-1 pt-1 scrollbar-hide"
            style={{
              paddingRight: 'max(1rem, env(safe-area-inset-right, 0px))',
              paddingLeft: 'max(0px, env(safe-area-inset-left, 0px))',
              marginLeft: '-1rem',
              marginRight: '-1rem'
            }}
          >
            {daysAround.map((d) => {
              const isSel = isSameDay(d, selectedDate)
              const isTod = isSameDay(d, new Date())
              return (
                <button
                  key={d.toISOString()}
                  onClick={() => handleDateChange(new Date(d))}
                  className={`flex-none w-16 h-14 inline-flex flex-col items-center justify-center rounded-xl border select-none ${isSel ? 'bg-orange-500 text-white border-orange-500' : 'bg-white text-gray-700 border-gray-200'} ${isTod ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-white' : ''}`}
                >
                  <div className={`text-[10px] font-medium ${isSel ? 'text-white/90' : 'text-gray-500'}`}>
                    {format(d, 'EEE').toUpperCase()}
                  </div>
                  <div className="text-sm font-semibold leading-none">{format(d, 'dd')}</div>
                </button>
              )
            })}
          </div>
        </div>
        {loading && <div className="text-center text-gray-500">Загрузка...</div>}

        {filteredTasks.map(task => (
          <div key={task.id} className="task-card overflow-hidden">
            <div className="flex gap-3 items-start">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (!isPastDate) {
                    toggleTask(task)
                  }
                }}
                disabled={isPastDate || togglingTasks.has(task.id)}
                className={`mt-1 w-5 h-5 rounded-md border-2 inline-flex items-center justify-center transition-colors ${task.completed ? 'bg-orange-500 border-orange-500 text-white' : 'bg-white border-orange-400 text-transparent'} ${isPastDate || togglingTasks.has(task.id) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                aria-pressed={task.completed}
                title={isPastDate ? 'Нельзя изменить статус для прошлых дат' : togglingTasks.has(task.id) ? 'Обработка...' : ''}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <div
                className={`flex-1 min-w-0 ${task.subtasks && task.subtasks.length > 0 ? 'cursor-pointer' : (isPastDate ? 'cursor-default' : 'cursor-pointer')}`}
                onClick={() => {
                  if (task.subtasks && task.subtasks.length > 0) {
                    toggleExpanded(task.id)
                  } else if (!isPastDate) {
                    onEditTask(task)
                  }
                }}
              >
                <div className="flex flex-wrap items-center gap-2 gap-y-2 mb-2">
                  <span className="text-lg">{TASK_CATEGORIES[task.category]?.icon || '📋'}</span>
                  <span className="text-sm bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                    {task.frequency === 'daily' ? 'Ежедневно' :
                      task.frequency === 'weekly' ? 'Еженедельно' : 'Ежемесячно'}
                  </span>
                  {task.streak > 0 && (
                    <span className="text-sm bg-orange-500 text-white px-2 py-1 rounded-full flex items-center gap-1">
                      🔥 {task.streak}
                    </span>
                  )}
                </div>

                <h3 className={`font-medium truncate ${task.completed ? 'line-through text-gray-500' : ''}`}>
                  {task.title}
                </h3>

                {task.description && (
                  <p className={`text-sm text-gray-500 mt-1 line-clamp-2 ${task.completed ? 'line-through' : ''}`}>
                    {task.description}
                  </p>
                )}

                {task.subtasks && task.subtasks.length > 0 && (
                  <p className="text-sm text-gray-500 mt-1">
                    {task.subtasks.filter(st => st.completed).length}/{task.subtasks.length} подзадач выполнено
                  </p>
                )}
              </div>

              <div className="flex gap-2 flex-shrink-0 ml-auto">
                {task.subtasks && task.subtasks.length > 0 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      if (!isPastDate && onEditTask) {
                        onEditTask(task)
                      }
                    }}
                    disabled={isPastDate}
                    className={`text-gray-400 ${isPastDate ? 'opacity-50 cursor-not-allowed' : 'hover:text-gray-600 cursor-pointer'}`}
                    title={isPastDate ? 'Нельзя редактировать задачу для прошлых дат' : 'Редактировать задачу'}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M18.5 2.5C18.8978 2.10218 19.4374 1.87868 20 1.87868C20.5626 1.87868 21.1022 2.10218 21.5 2.5C21.8978 2.89782 22.1213 3.43739 22.1213 4C22.1213 4.56261 21.8978 5.10218 21.5 5.5L12 15L8 16L9 12L18.5 2.5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (!isPastDate && onCreateSubtask) {
                      onCreateSubtask(task)
                    }
                  }}
                  disabled={isPastDate}
                  className={`text-gray-400 ${isPastDate ? 'opacity-50 cursor-not-allowed' : 'hover:text-gray-600 cursor-pointer'}`}
                  title={isPastDate ? 'Нельзя добавить подзадачу для прошлых дат' : 'Добавить подзадачу'}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (!isPastDate) {
                      deleteTask(task)
                    }
                  }}
                  disabled={isPastDate || deletingTasks.has(task.id)}
                  className={`text-red-400 ${isPastDate || deletingTasks.has(task.id) ? 'opacity-50 cursor-not-allowed' : 'hover:text-red-600 cursor-pointer'}`}
                  title={isPastDate ? 'Нельзя удалить задачу для прошлых дат' : deletingTasks.has(task.id) ? 'Удаление...' : 'Удалить задачу'}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M3 6H5H21M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>
            </div>

            {expandedTasks.has(task.id) && task.subtasks && task.subtasks.length > 0 && (
              <div className="mt-3 ml-8 space-y-2 border-l-2 border-gray-200 pl-4">
                {task.subtasks.map(subtask => (
                  <div key={subtask.id} className="flex items-center gap-3 py-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (!isPastDate) {
                          toggleSubtask(subtask, task)
                        }
                      }}
                      disabled={isPastDate || togglingSubtasks.has(subtask.id)}
                      className={`w-5 h-5 rounded-md border-2 inline-flex items-center justify-center transition-colors flex-shrink-0 ${subtask.completed
                        ? 'bg-orange-500 border-orange-500 text-white'
                        : 'bg-white border-orange-400 text-transparent'
                        } ${isPastDate || togglingSubtasks.has(subtask.id) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                      aria-pressed={subtask.completed}
                      title={isPastDate ? 'Нельзя изменить статус для прошлых дат' : togglingSubtasks.has(subtask.id) ? 'Обработка...' : ''}
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                        <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>

                    <div
                      className={`flex-1 min-w-0 ${isPastDate ? 'cursor-default' : 'cursor-pointer'}`}
                      onClick={(e) => {
                        e.stopPropagation()
                        if (!isPastDate && onEditSubtask) {
                          onEditSubtask(subtask, task)
                        }
                      }}
                    >
                      <h4 className={`text-sm ${subtask.completed ? 'line-through text-gray-500' : 'text-gray-700'}`}>
                        {subtask.title}
                      </h4>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (!isPastDate && confirm('Удалить подзадачу?')) {
                          deleteSubtask(subtask.id, task.id)
                        }
                      }}
                      disabled={isPastDate || deletingSubtasks.has(subtask.id)}
                      className={`text-red-400 flex-shrink-0 ${isPastDate || deletingSubtasks.has(subtask.id) ? 'opacity-50 cursor-not-allowed' : 'hover:text-red-600 cursor-pointer'}`}
                      title={isPastDate ? 'Нельзя удалить подзадачу для прошлых дат' : deletingSubtasks.has(subtask.id) ? 'Удаление...' : 'Удалить подзадачу'}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <path d="M3 6H5H21M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {filteredTasks.length === 0 && !loading && (
          <div className="text-center text-gray-500 py-8">
            <div className="text-4xl mb-2">📋</div>
            <div>Нет задач</div>
          </div>
        )}
      </div>

      <button onClick={onCreateTask} className="floating-btn">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </div>
  )
}

