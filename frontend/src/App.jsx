import React, { useEffect, useMemo, useState, useRef, useCallback, memo } from 'react'
// Импортируем только нужные компоненты из recharts
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import { format, isSameDay, isToday, startOfMonth, endOfMonth, eachDayOfInterval, startOfDay, getDay } from 'date-fns'
import { ru } from 'date-fns/locale'

// Импорты утилит и хуков
import { createApiClient, invalidateCache } from './utils/api.js'
import { useInitData, useTelegram } from './hooks/useTelegram.js'
import { TASK_CATEGORIES, FREQUENCY_OPTIONS, MOOD_OPTIONS } from './constants/index.js'
import { formatDateForAPI, getDaysAround } from './utils/dateUtils.js'

// Компонент для создания новой задачи
function CreateTaskPage({ onBack, onTaskCreated, task = null }) {
  const initData = useInitData()
  const isEditing = task !== null
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('personal')
  const [frequency, setFrequency] = useState('daily')
  const [loading, setLoading] = useState(false)


  // Инициализация полей при редактировании
  useEffect(() => {
    if (isEditing && task) {
      setTitle(task.title || '')
      setDescription(task.description || '')
      setCategory(task.category || 'personal')
      setFrequency(task.frequency || 'daily')
    } else {
      // Сброс при создании новой задачи
      setTitle('')
      setDescription('')
      setCategory('personal')
      setFrequency('daily')
    }
  }, [isEditing, task])

  const api = useMemo(() => createApiClient(initData), [initData])

  const createTask = useCallback(async () => {
    if (!title.trim()) return

    setLoading(true)
    try {
      if (isEditing) {
        // Обновление существующей задачи
        await api(`/task/${task.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            title: title.trim(),
            description: description.trim(),
            category: category,
            frequency: frequency,
          })
        })
      } else {
        // Создание новой задачи
        await api('/task', {
          method: 'POST',
          body: JSON.stringify({
            title: title.trim(),
            description: description.trim(),
            category: category,
            frequency: frequency,
          })
        })
      }

      invalidateCache('/tasks') // Инвалидируем кэш задач
      invalidateCache('/stats') // Инвалидируем кэш статистики
      invalidateCache('/habits') // Инвалидируем кэш привычек

      onTaskCreated()
    } catch (error) {
      console.error(`Error ${isEditing ? 'updating' : 'creating'} task:`, error)
      alert(`Ошибка при ${isEditing ? 'обновлении' : 'создании'} задачи`)
    } finally {
      setLoading(false)
    }
  }, [api, title, description, category, frequency, isEditing, task, onTaskCreated])

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
        {/* <p className="text-gray-600 text-sm mt-1">Создайте задачу для отслеживания</p> */}
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
          <label className="block text-sm font-medium text-gray-700 mb-2">Описание (опционально)</label>
          <input
            value={description}
            onChange={e => setDescription(e.target.value)}
            className="input"
            placeholder="Добавьте описание задачи"
          />
        </div>

        {/* Категория */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">Категория</label>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(TASK_CATEGORIES).map(([key, value]) => (
              <div
                key={key}
                className={`category-card ${category === key ? 'selected' : ''}`}
                onClick={() => setCategory(key)}
              >
                <div className="text-center">
                  <div className="text-2xl mb-2">{value.icon}</div>
                  <div className="text-sm font-medium">{value.name}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Периодичность */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">Периодичность</label>
          <div className="space-y-2">
            {FREQUENCY_OPTIONS.map((option) => (
              <div
                key={option.value}
                className={`frequency-option ${frequency === option.value ? 'selected' : ''}`}
                onClick={() => setFrequency(option.value)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{option.label}</div>
                    <div className="text-sm text-gray-500">{option.description}</div>
                  </div>
                  {frequency === option.value && (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
              </div>
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
            onClick={createTask}
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

// Компонент для создания/редактирования подзадачи
function CreateSubtaskPage({ onBack, onSubtaskCreated, parentTask, subtask = null }) {
  const initData = useInitData()
  const isEditing = subtask !== null
  const [title, setTitle] = useState(subtask?.title || '')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isEditing && subtask) {
      setTitle(subtask.title || '')
    } else {
      setTitle('')
    }
  }, [isEditing, subtask])

  const api = useMemo(() => createApiClient(initData), [initData])

  const createSubtask = useCallback(async () => {
    if (!title.trim()) return

    setLoading(true)
    try {
      if (isEditing) {
        // Обновление подзадачи
        await api(`/subtask/${subtask.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            title: title.trim(),
          })
        })
        invalidateCache('/tasks') // Инвалидируем кэш задач
        onSubtaskCreated()
      } else {
        await api('/subtask', {
          method: 'POST',
          body: JSON.stringify({
            task_id: parentTask.id,
            title: title.trim(),
          })
        })
        invalidateCache('/tasks') // Инвалидируем кэш задач
        onSubtaskCreated()
      }
    } catch (error) {
      console.error(`Error ${isEditing ? 'updating' : 'creating'} subtask:`, error)
      alert(`Ошибка при ${isEditing ? 'обновлении' : 'создании'} подзадачи`)
    } finally {
      setLoading(false)
    }
  }, [api, title, isEditing, subtask, parentTask, onSubtaskCreated])

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
            onClick={createSubtask}
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

// Компонент для страницы задач
function TasksPage({ onCreateTask, onEditTask, onTaskUpdated, onCreateSubtask, onEditSubtask }) {
  const initData = useInitData()
  const [tasks, setTasks] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [selectedDate, setSelectedDate] = useState(new Date())
  const ribbonRef = useRef(null)
  const [expandedTasks, setExpandedTasks] = useState(new Set()) // Отслеживаем развернутые задачи
  const taskUpdateVersionsRef = useRef(new Map()) // Отслеживаем версии обновлений задач для предотвращения race conditions
  const subtaskUpdateVersionsRef = useRef(new Map()) // Отслеживаем версии обновлений подзадач


  const api = useMemo(() => createApiClient(initData), [initData])

  const loadTasks = useCallback(async () => {
    setLoading(true)
    try {
      // Форматируем выбранную дату для запроса
      const dateStr = formatDateForAPI(selectedDate)
      const data = await api(`/tasks?date=${dateStr}`)
      setTasks(data)
    } finally {
      setLoading(false)
    }
  }, [api, selectedDate])

  const loadTasksRef = useRef(null)
  loadTasksRef.current = loadTasks

  useEffect(() => {
    loadTasks()
  }, [loadTasks]) // Перезагружаем задачи при изменении выбранной даты

  // Перезагружаем задачи при монтировании компонента (ключ изменился)
  // Это обеспечит актуальный список после возврата со страницы редактирования

  // Передаем функцию обновления наверх
  useEffect(() => {
    if (onTaskUpdated) {
      onTaskUpdated(() => {
        if (loadTasksRef.current) {
          loadTasksRef.current()
        }
      })
    }
  }, [onTaskUpdated])

  // Мемоизируем обработчики для предотвращения лишних ререндеров
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

  // // Бэкенд уже фильтрует задачи по выбранной дате, поэтому используем все полученные задачи
  // const tasksForSelectedDay = tasks

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
    // Показываем только прошлые дни и сегодня
    for (let i = 30; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(today.getDate() - i)
      days.push(d)
    }
    return days
  }, [])

  // Восстанавливаем позицию скролла или устанавливаем в конец (на текущую дату) без анимации
  useEffect(() => {
    if (ribbonRef.current && daysAround.length > 0) {
      // Используем requestAnimationFrame для установки позиции сразу после рендера, без видимой прокрутки
      const rafId = requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (!ribbonRef.current) return

          // Пытаемся восстановить сохраненную позицию скролла
          const savedScrollPosition = localStorage.getItem('calendarScrollPosition')
          if (savedScrollPosition !== null) {
            ribbonRef.current.scrollLeft = parseInt(savedScrollPosition, 10)
          } else {
            // Если сохраненной позиции нет, устанавливаем скролл в конец (на текущую дату) без анимации
            const hasScrolledBefore = localStorage.getItem('calendarHasScrolled')
            if (!hasScrolledBefore) {
              const today = new Date()
              const todayIndex = daysAround.findIndex(d => isSameDay(d, today))

              if (todayIndex !== -1 && ribbonRef.current) {
                const todayButton = ribbonRef.current.children[todayIndex]
                if (todayButton) {
                  // Вычисляем позицию для центрирования текущей даты
                  const container = ribbonRef.current
                  const buttonLeft = todayButton.offsetLeft
                  const buttonWidth = todayButton.offsetWidth
                  const containerWidth = container.offsetWidth

                  // Устанавливаем scrollLeft сразу, без анимации
                  container.scrollLeft = buttonLeft - (containerWidth / 2) + (buttonWidth / 2)

                  // Сохраняем позицию
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

  // Сохраняем позицию скролла при прокрутке
  useEffect(() => {
    const ribbon = ribbonRef.current
    if (!ribbon) return

    const handleScroll = () => {
      localStorage.setItem('calendarScrollPosition', ribbon.scrollLeft.toString())
    }

    ribbon.addEventListener('scroll', handleScroll)
    return () => ribbon.removeEventListener('scroll', handleScroll)
  }, [])

  // Проверяем, является ли выбранная дата прошлой
  const isPastDate = useMemo(() => {
    const today = startOfDay(new Date())
    const selected = startOfDay(selectedDate)
    return selected < today
  }, [selectedDate])


  const toggleTask = useCallback(async (task) => {
    // Блокируем изменение статуса для прошлых дат
    if (isPastDate) {
      return
    }

    // Создаем уникальную версию для этого обновления
    const updateVersion = Date.now()
    taskUpdateVersionsRef.current.set(task.id, updateVersion)

    // Оптимистичное обновление - сразу меняем состояние в UI
    const newCompletedState = !task.completed

    // Мгновенно обновляем UI используя функциональное обновление
    setTasks(prev => prev.map(t => {
      if (t.id === task.id) {
        // Берем актуальное состояние из предыдущего состояния, а не из переданного task
        const currentTask = t
        const updatedTask = { ...currentTask, completed: newCompletedState }

        // Если задача отменяется, отменяем все подзадачи в UI
        if (!newCompletedState && currentTask.subtasks && currentTask.subtasks.length > 0) {
          updatedTask.subtasks = (currentTask.subtasks || []).map(st => ({ ...st, completed: false }))
        }

        return updatedTask
      }
      return t
    }))

    // Затем синхронизируем с сервером
    try {
      const updated = await api(`/task/${task.id}/complete`, { method: 'POST' })

      // Проверяем, не устарел ли этот ответ (было ли более новое обновление)
      const currentVersion = taskUpdateVersionsRef.current.get(task.id)
      if (currentVersion !== updateVersion) {
        // Это устаревший ответ, игнорируем его
        return
      }

      invalidateCache('/tasks') // Инвалидируем кэш задач
      invalidateCache('/stats') // Инвалидируем кэш статистики
      invalidateCache('/habits') // Инвалидируем кэш привычек

      // Если задача отменяется (completed стал false), отменяем все подзадачи на сервере
      if (!updated.completed) {
        // Используем актуальное состояние из tasks
        setTasks(prev => {
          const currentTask = prev.find(t => t.id === task.id)
          if (!currentTask || !currentTask.subtasks || currentTask.subtasks.length === 0) {
            return prev.map(t => t.id === task.id ? { ...updated, subtasks: [] } : t)
          }

          // Отменяем все выполненные подзадачи в фоне
          const uncompletedSubtasks = currentTask.subtasks.map(async (subtask) => {
            if (subtask.completed) {
              try {
                return await api(`/subtask/${subtask.id}/complete`, { method: 'POST' })
              } catch (error) {
                console.error(`Error uncompleting subtask ${subtask.id}:`, error)
                return subtask
              }
            }
            return subtask
          })

          // Ждем завершения всех операций
          Promise.all(uncompletedSubtasks).then(updatedSubtasks => {
            // Проверяем актуальность перед обновлением
            const latestVersion = taskUpdateVersionsRef.current.get(task.id)
            if (latestVersion === updateVersion) {
              setTasks(prevTasks => prevTasks.map(t => {
                if (t.id === task.id) {
                  return { ...updated, subtasks: updatedSubtasks }
                }
                return t
              }))
            }
          })

          return prev.map(t => t.id === task.id ? { ...updated, subtasks: currentTask.subtasks } : t)
        })
      } else {
        // Обновляем задачу с данными с сервера, используя актуальное состояние
        setTasks(prev => prev.map(t => {
          if (t.id === task.id) {
            // Сохраняем подзадачи если они есть из актуального состояния
            return { ...updated, subtasks: t.subtasks || [] }
          }
          return t
        }))
      }
    } catch (error) {
      console.error('Error toggling task:', error)
      // Проверяем актуальность перед откатом
      const currentVersion = taskUpdateVersionsRef.current.get(task.id)
      if (currentVersion === updateVersion) {
        // Откатываем изменения при ошибке только если это актуальное обновление
        setTasks(prev => prev.map(t => {
          if (t.id === task.id) {
            // Откатываем к предыдущему состоянию из актуального состояния
            return { ...t, completed: !newCompletedState }
          }
          return t
        }))
      }
    }
  }, [api, isPastDate])

  const deleteTask = useCallback(async (task) => {
    // Блокируем удаление задач для прошлых дат
    if (isPastDate) {
      return
    }

    try {
      await api(`/task/${task.id}`, { method: 'DELETE' })
      invalidateCache('/tasks') // Инвалидируем кэш задач
      invalidateCache('/stats') // Инвалидируем кэш статистики
      invalidateCache('/habits') // Инвалидируем кэш привычек
      setTasks(prev => prev.filter(t => t.id !== task.id))
    } catch (error) {
      console.error('Error deleting task:', error)
    }
  }, [api, isPastDate])

  // Используем уже мемоизированную функцию
  const toggleExpanded = toggleTaskExpanded

  const toggleSubtask = useCallback(async (subtask, parentTask) => {
    // Блокируем изменение статуса для прошлых дат
    if (isPastDate) {
      return
    }

    // Создаем уникальную версию для этого обновления
    const updateVersion = Date.now()
    subtaskUpdateVersionsRef.current.set(subtask.id, updateVersion)

    // Оптимистичное обновление - сразу меняем состояние в UI
    // Используем функциональное обновление для получения актуального состояния
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

          // Проверяем, все ли подзадачи выполнены
          const allCompleted = updatedSubtasks.length > 0 && updatedSubtasks.every(st => st.completed)

          // Автоматически обновляем статус задачи в UI
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

    // Если не удалось найти подзадачу, выходим
    if (newCompletedState === null) {
      return
    }

    // Затем синхронизируем с сервером
    try {
      const updated = await api(`/subtask/${subtask.id}/complete`, { method: 'POST' })

      // Проверяем, не устарел ли этот ответ
      const currentVersion = subtaskUpdateVersionsRef.current.get(subtask.id)
      if (currentVersion !== updateVersion) {
        // Это устаревший ответ, игнорируем его
        return
      }

      invalidateCache('/tasks') // Инвалидируем кэш задач

      // Обновляем подзадачу в задаче с данными с сервера, используя актуальное состояние
      setTasks(prev => {
        const currentParentTask = prev.find(t => t.id === parentTask.id)
        if (!currentParentTask) return prev

        return prev.map(t => {
          if (t.id === parentTask.id) {
            const updatedSubtasks = (t.subtasks || []).map(st =>
              st.id === subtask.id ? updated : st
            )

            // Проверяем, все ли подзадачи выполнены
            const allCompleted = updatedSubtasks.length > 0 && updatedSubtasks.every(st => st.completed)

            // Если все подзадачи выполнены и задача еще не выполнена, автоматически отмечаем задачу
            if (allCompleted && !t.completed) {
              // Автоматически отмечаем задачу через API в фоне
              api(`/task/${t.id}/complete`, { method: 'POST' }).then(updatedTask => {
                // Проверяем актуальность перед обновлением
                const latestVersion = subtaskUpdateVersionsRef.current.get(subtask.id)
                if (latestVersion === updateVersion) {
                  setTasks(prevTasks => prevTasks.map(task => {
                    if (task.id === updatedTask.id) {
                      // Используем актуальные подзадачи
                      const currentTask = prevTasks.find(tt => tt.id === task.id)
                      return { ...updatedTask, subtasks: currentTask?.subtasks || updatedSubtasks }
                    }
                    return task
                  }))
                }
              }).catch(error => {
                console.error('Error auto-completing task:', error)
              })
            }
            // Если хотя бы одна подзадача не выполнена и задача выполнена, автоматически отменяем задачу
            else if (!allCompleted && t.completed) {
              // Автоматически отменяем задачу через API в фоне
              api(`/task/${t.id}/complete`, { method: 'POST' }).then(updatedTask => {
                // Проверяем актуальность перед обновлением
                const latestVersion = subtaskUpdateVersionsRef.current.get(subtask.id)
                if (latestVersion === updateVersion) {
                  setTasks(prevTasks => prevTasks.map(task => {
                    if (task.id === updatedTask.id) {
                      // Используем актуальные подзадачи
                      const currentTask = prevTasks.find(tt => tt.id === task.id)
                      return { ...updatedTask, subtasks: currentTask?.subtasks || updatedSubtasks }
                    }
                    return task
                  }))
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
      // Проверяем актуальность перед откатом
      const currentVersion = subtaskUpdateVersionsRef.current.get(subtask.id)
      if (currentVersion === updateVersion && newCompletedState !== null) {
        // Откатываем изменения при ошибке только если это актуальное обновление
        setTasks(prev => prev.map(t => {
          if (t.id === parentTask.id) {
            const updatedSubtasks = (t.subtasks || []).map(st =>
              st.id === subtask.id ? { ...st, completed: !newCompletedState } : st
            )
            // Пересчитываем статус задачи
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
    }
  }, [api, isPastDate])

  const deleteSubtask = useCallback(async (subtaskId, parentTaskId) => {
    // Блокируем удаление подзадач для прошлых дат
    if (isPastDate) {
      return
    }

    try {
      await api(`/subtask/${subtaskId}`, { method: 'DELETE' })
      invalidateCache('/tasks') // Инвалидируем кэш задач
      setTasks(prev => prev.map(t => {
        if (t.id === parentTaskId) {
          const updatedSubtasks = (t.subtasks || []).filter(st => st.id !== subtaskId)

          // Проверяем, все ли оставшиеся подзадачи выполнены
          const allCompleted = updatedSubtasks.length > 0 && updatedSubtasks.every(st => st.completed)

          // Если задача была выполнена, но теперь не все подзадачи выполнены, отменяем задачу
          if (!allCompleted && t.completed) {
            // Автоматически отменяем задачу через API
            api(`/task/${t.id}/complete`, { method: 'POST' }).then(updatedTask => {
              // Обновляем задачу в списке, сохраняя подзадачи
              setTasks(prevTasks => prevTasks.map(task => {
                if (task.id === updatedTask.id) {
                  // Сохраняем подзадачи при обновлении задачи
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
    }
  }, [api, isPastDate])

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      {/* Header */}
      <div className="bg-white px-4 py-4">
        <h1 className="text-xl font-semibold">Мои задачи</h1>

        {/* Filter tabs */}
        <div className="flex gap-2 mt-4">
          {[
            { key: 'all', label: 'Все' },
            { key: 'active', label: 'Активные' },
            { key: 'completed', label: 'Выполненные' }
          ].map(tab => (
            <button
              key={tab.key}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${filter === tab.key ? 'tab-active' : 'tab-inactive'
                }`}
              onClick={() => handleFilterChange(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-4 py-4 pb-24 space-y-3">
        {/* Календарная лента дат */}
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
                disabled={isPastDate}
                className={`mt-1 w-5 h-5 rounded-md border-2 inline-flex items-center justify-center transition-colors ${task.completed ? 'bg-orange-500 border-orange-500 text-white' : 'bg-white border-orange-400 text-transparent'} ${isPastDate ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                aria-pressed={task.completed}
                title={isPastDate ? 'Нельзя изменить статус для прошлых дат' : ''}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <div
                className={`flex-1 min-w-0 ${task.subtasks && task.subtasks.length > 0 ? 'cursor-pointer' : (isPastDate ? 'cursor-default' : 'cursor-pointer')}`}
                onClick={() => {
                  // Если есть подзадачи - раскрываем их, иначе открываем редактирование
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
                  disabled={isPastDate}
                  className={`text-red-400 ${isPastDate ? 'opacity-50 cursor-not-allowed' : 'hover:text-red-600 cursor-pointer'}`}
                  title={isPastDate ? 'Нельзя удалить задачу для прошлых дат' : 'Удалить задачу'}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M3 6H5H21M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>
            </div >

            {/* Список подзадач */}
            {
              expandedTasks.has(task.id) && task.subtasks && task.subtasks.length > 0 && (
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
                        disabled={isPastDate}
                        className={`w-5 h-5 rounded-md border-2 inline-flex items-center justify-center transition-colors flex-shrink-0 ${subtask.completed
                          ? 'bg-orange-500 border-orange-500 text-white'
                          : 'bg-white border-orange-400 text-transparent'
                          } ${isPastDate ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                        aria-pressed={subtask.completed}
                        title={isPastDate ? 'Нельзя изменить статус для прошлых дат' : ''}
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
                        disabled={isPastDate}
                        className={`text-red-400 flex-shrink-0 ${isPastDate ? 'opacity-50 cursor-not-allowed' : 'hover:text-red-600 cursor-pointer'}`}
                        title={isPastDate ? 'Нельзя удалить подзадачу для прошлых дат' : 'Удалить подзадачу'}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                          <path d="M3 6H5H21M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )
            }
          </div >
        ))
        }

        {
          filteredTasks.length === 0 && !loading && (
            <div className="text-center text-gray-500 py-8">
              <div className="text-4xl mb-2">📋</div>
              <div>Нет задач</div>
            </div>
          )
        }
      </div >

      {/* Floating Action Button */}
      < button onClick={onCreateTask} className="floating-btn" >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button >
    </div >
  )
}

// Компонент для страницы статистики
function StatisticsPage() {
  const initData = useInitData()
  const [period, setPeriod] = useState('day') // Стартовый период - день
  const [stats, setStats] = useState(null)
  const [habitsStats, setHabitsStats] = useState([])
  const [loading, setLoading] = useState(false)

  const api = useMemo(() => createApiClient(initData), [initData])

  const loadStats = useCallback(async (p) => {
    setLoading(true)
    try {
      const data = await api(`/stats?period=${p}`)
      setStats(data)
    } catch (error) {
      console.error('Error loading stats:', error)
      // Устанавливаем пустую статистику при ошибке
      setStats({
        completed: 0,
        in_progress: 0,
        upcoming: 0,
        total: 0
      })
    } finally {
      setLoading(false)
    }
  }, [api])

  const loadHabitsStats = useCallback(async () => {
    try {
      const data = await api('/habits')
      setHabitsStats(data)
    } catch (error) {
      console.error('Error loading habits stats:', error)
      setHabitsStats([])
    }
  }, [api])

  useEffect(() => {
    loadStats(period)
    loadHabitsStats()
  }, [period, loadStats, loadHabitsStats])

  const handlePeriodChange = useCallback((e) => {
    setPeriod(e.target.value)
  }, [])

  // Мемоизируем данные для графика
  const pieData = useMemo(() => {
    if (!stats || stats.total === 0) return []

    if (stats.completed === stats.total) {
      return [{ name: 'Выполнено', value: 100, color: '#10B981' }]
    }

    return [
      { name: 'Выполнено', value: stats.completed || 0, color: '#10B981' },
      { name: 'Не выполнено', value: stats.in_progress || 0, color: '#8B5CF6' },
    ]
  }, [stats])

  // Мемоизируем процент выполнения
  const completionPercentage = useMemo(() => {
    if (!stats || stats.total === 0) return 0
    return Math.round(((stats.completed || 0) / stats.total) * 100)
  }, [stats])

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      {/* Header */}
      <div className="bg-white px-4 py-4">
        <h1 className="text-xl font-semibold">Статистика</h1>
      </div>

      <div className="p-4 pb-24 space-y-6">
        {/* Активность */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Активность</h2>
            <select
              value={period}
              onChange={handlePeriodChange}
              className="bg-gray-100 rounded-lg px-3 py-1 text-sm"
            >
              <option value="day">День</option>
              <option value="week">Неделя</option>
              <option value="month">Месяц</option>
              <option value="all">Всего</option>
            </select>
          </div>

          <div className="flex items-center gap-6">
            {/* График */}
            {loading ? (
              <div className="flex items-center justify-center w-32 h-32">
                <div className="text-sm text-gray-400">Загрузка...</div>
              </div>
            ) : stats ? (
              <div className="relative w-32 h-32">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={false}
                      outerRadius={50}
                      innerRadius={0}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>

                {/* Центральный текст - только проценты */}
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <div className="text-xl font-bold text-gray-800">
                    {completionPercentage}%
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center w-32 h-32">
                <div className="text-sm text-gray-400">Нет данных</div>
              </div>
            )}

            {/* Легенда */}
            <div className="flex-1 space-y-2">
              {loading ? (
                <div className="text-sm text-gray-500">Загрузка...</div>
              ) : stats ? (
                <>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-sm text-gray-700">
                      {stats.completed || 0} Выполнено
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                    <span className="text-sm text-gray-700">
                      {stats.in_progress || 0} Не выполнено
                    </span>
                  </div>
                </>
              ) : (
                <div className="text-sm text-gray-500">Нет данных</div>
              )}
            </div>
          </div>
        </div>

        {/* Привычки */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Привычки</h2>
          <div className="space-y-3">
            {habitsStats.length === 0 ? (
              <div className="text-center text-gray-500 py-4">
                <div className="text-4xl mb-2">📋</div>
                <div>Нет привычек</div>
              </div>
            ) : (
              habitsStats.map((habit) => {
                const categoryInfo = TASK_CATEGORIES[habit.category] || { name: habit.category, icon: '📋' }
                const maxStreak = habit.max_streak || 0
                const filledCircles = Math.min(maxStreak, 7)
                const showFire = maxStreak > 7

                // Форматируем текст стрика
                let streakText = 'Нет стрика'
                if (maxStreak === 1) {
                  streakText = '1 день'
                } else if (maxStreak > 1 && maxStreak <= 4) {
                  streakText = `${maxStreak} дня`
                } else if (maxStreak > 4) {
                  streakText = `${maxStreak} дней`
                }

                return (
                  <div key={habit.category} className="habit-item">
                    <div className="text-2xl">{categoryInfo.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <div className="font-medium">{categoryInfo.name}</div>
                        {showFire && (
                          <span className="text-sm bg-orange-500 text-white px-2 py-1 rounded-full flex items-center gap-1">
                            🔥 {maxStreak}
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-orange-500">{streakText}</div>
                    </div>
                    <div className="streak-dots">
                      {Array.from({ length: 7 }, (_, i) => (
                        <div key={i} className={`streak-dot ${i < filledCircles ? 'active' : 'inactive'}`} />
                      ))}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// SVG иконка настроения
function MoodIcon({ value, size = 20 }) {
  const map = {
    very_bad: { fill: '#EF4444', stroke: '#B91C1C', mouth: 'down' },
    bad: { fill: '#FCA5A5', stroke: '#EF4444', mouth: 'down' },
    neutral: { fill: '#FDE047', stroke: '#CA8A04', mouth: 'flat' },
    good: { fill: '#86EFAC', stroke: '#16A34A', mouth: 'up' },
    very_good: { fill: '#22C55E', stroke: '#15803D', mouth: 'up' },
  }
  const c = map[value] || map.neutral
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <circle cx="24" cy="24" r="22" fill={c.fill} stroke={c.stroke} strokeWidth="2" />
      <circle cx="17" cy="20" r="3" fill="#1F2937" />
      <circle cx="31" cy="20" r="3" fill="#1F2937" />
      {c.mouth === 'up' && <path d="M16 30 C 20 36, 28 36, 32 30" stroke="#1F2937" strokeWidth="3" fill="none" strokeLinecap="round" />}
      {c.mouth === 'down' && <path d="M16 34 C 20 28, 28 28, 32 34" stroke="#1F2937" strokeWidth="3" fill="none" strokeLinecap="round" />}
      {c.mouth === 'flat' && <path d="M16 32 L 32 32" stroke="#1F2937" strokeWidth="3" strokeLinecap="round" />}
    </svg>
  )
}

// Компонент для страницы журнала
function JournalPage({ preloadedNotes = [], preloadedMonthMoodMap = {} }) {
  const initData = useInitData()
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [notes, setNotes] = useState(preloadedNotes)
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newNote, setNewNote] = useState('')
  const [selectedMood, setSelectedMood] = useState('')
  const [monthMoodMap, setMonthMoodMap] = useState(preloadedMonthMoodMap)
  const [editingNote, setEditingNote] = useState(null)
  const [editContent, setEditContent] = useState('')
  const [editMood, setEditMood] = useState('')


  const api = useMemo(() => createApiClient(initData), [initData])

  const loadNotes = useCallback(async (date, showLoading = true) => {
    if (showLoading) {
      setLoading(true)
    }
    try {
      const dateStr = format(date, 'yyyy-MM-dd')
      const data = await api(`/notes?date=${dateStr}`)
      setNotes(data)
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }, [api])

  const normalizeMood = (mood) => {
    switch (mood) {
      case '😡': return 'very_bad'
      case '😞': return 'bad'
      case '😐': return 'neutral'
      case '🙂': return 'good'
      case '🤩': return 'very_good'
      default: return mood
    }
  }

  const moodToClasses = (mood) => {
    const m = normalizeMood(mood)
    switch (m) {
      case 'very_good':
        return 'bg-green-600 text-white'
      case 'good':
        return 'bg-green-300 text-gray-900'
      case 'neutral':
        return 'bg-yellow-300 text-gray-900'
      case 'bad':
        return 'bg-red-300 text-gray-900'
      case 'very_bad':
        return 'bg-red-600 text-white'
      default:
        return ''
    }
  }

  const loadMonthMood = useCallback(async (date) => {
    try {
      // Загружаем все заметки за месяц одним запросом
      const year = date.getFullYear()
      const month = date.getMonth() + 1 // getMonth() возвращает 0-11
      const data = await api(`/notes?year=${year}&month=${month}`)

      const map = {}
      if (Array.isArray(data)) {
        // Группируем по датам, берем первую заметку для каждой даты
        const notesByDate = {}
        data.forEach(note => {
          if (note.date && !notesByDate[note.date]) {
            notesByDate[note.date] = note
          }
        })

        // Создаем карту настроений
        Object.entries(notesByDate).forEach(([dateStr, note]) => {
          if (note?.mood) {
            map[dateStr] = moodToClasses(note.mood)
          }
        })
      }
      setMonthMoodMap(map)
    } catch (e) {
      console.error('Error loading month mood:', e)
      // В случае ошибки просто не обновляем карту
    }
  }, [api])

  const createNote = async () => {
    if (!selectedMood) {
      alert('Пожалуйста, выберите настроение')
      return
    }
    try {
      const created = await api('/notes', {
        method: 'POST',
        body: JSON.stringify({
          content: newNote.trim(),
          date: format(selectedDate, 'yyyy-MM-dd'),
          mood: selectedMood
        })
      })
      setNotes(prev => [created, ...prev])
      setNewNote('')
      setShowCreateForm(false)
      const dateStr = formatDateForAPI(selectedDate)
      setMonthMoodMap(prev => ({ ...prev, [dateStr]: moodToClasses(selectedMood) }))
    } catch (err) {
      console.error(err)
      alert('Не удалось добавить заметку')
    }
  }

  const cancelCreate = () => {
    setNewNote('')
    setShowCreateForm(false)
  }

  const startEdit = (note) => {
    setEditingNote(note)
    setEditContent(note.content || '')
    setEditMood(normalizeMood(note.mood || 'neutral'))
  }

  const cancelEdit = () => {
    setEditingNote(null)
    setEditContent('')
    setEditMood('')
  }

  const saveEdit = async () => {
    if (!editingNote) return
    if (!editMood) {
      alert('Пожалуйста, выберите настроение')
      return
    }
    const payload = {
      content: editContent.trim(),
      date: format(selectedDate, 'yyyy-MM-dd'),
      mood: editMood,
    }
    try {
      // Попробуем PUT, если не поддерживается — fallback: DELETE+POST
      try {
        const updated = await api(`/notes/${editingNote.id}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        })
        setNotes(prev => prev.map(n => n.id === editingNote.id ? updated : n))
      } catch (e) {
        await api(`/notes/${editingNote.id}`, { method: 'DELETE' })
        const created = await api('/notes', { method: 'POST', body: JSON.stringify(payload) })
        setNotes(prev => [created, ...prev.filter(n => n.id !== editingNote.id)])
      }
      const dateStr = formatDateForAPI(selectedDate)
      setMonthMoodMap(prev => ({ ...prev, [dateStr]: moodToClasses(editMood) }))
      cancelEdit()
    } catch (err) {
      console.error(err)
      alert('Не удалось сохранить изменения')
    }
  }

  useEffect(() => {
    // Загружаем заметки только если выбранная дата изменилась или это не сегодняшняя дата
    const today = new Date()
    const isToday = isSameDay(selectedDate, today)

    // Если это сегодня и у нас есть предзагруженные заметки, используем их сразу
    if (isToday && preloadedNotes.length >= 0) {
      // Используем предзагруженные заметки сразу (даже если массив пустой)
      setNotes(preloadedNotes)
      setLoading(false)
      // Обновляем в фоне для актуальности (но не показываем loading)
      loadNotes(selectedDate, false).catch(() => {
        // Игнорируем ошибки фоновой загрузки
      })
    } else {
      // Иначе загружаем заново
      loadNotes(selectedDate, true)
    }
    setShowCreateForm(false)
  }, [selectedDate, loadNotes, preloadedNotes])

  useEffect(() => {
    // Если у нас есть предзагруженные данные для текущего месяца, используем их
    const today = new Date()
    const isCurrentMonth = selectedDate.getFullYear() === today.getFullYear() &&
      selectedDate.getMonth() === today.getMonth()

    if (isCurrentMonth && Object.keys(preloadedMonthMoodMap).length > 0) {
      setMonthMoodMap(preloadedMonthMoodMap)
    } else {
      // Иначе загружаем заново
      loadMonthMood(selectedDate)
    }
  }, [selectedDate.getFullYear(), selectedDate.getMonth(), loadMonthMood, preloadedMonthMoodMap])

  const calendarDays = useMemo(() => {
    const start = startOfMonth(selectedDate)
    const end = endOfMonth(selectedDate)
    const days = eachDayOfInterval({ start, end })

    // Добавляем пустые дни в начале месяца
    const firstDay = getDay(start) === 0 ? 6 : getDay(start) - 1
    const emptyDays = Array(firstDay).fill(null)

    return [...emptyDays, ...days]
  }, [selectedDate])

  const goToPreviousMonth = useCallback(() => {
    setSelectedDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))
  }, [])

  const goToNextMonth = useCallback(() => {
    setSelectedDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))
  }, [])

  const handleDateSelect = useCallback((day) => {
    setSelectedDate(day)
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      {/* Header */}
      <div className="bg-white px-4 py-4">
        <h1 className="text-xl font-semibold">Журнал</h1>
      </div>

      <div className="p-4 pb-24 space-y-6">
        {/* Календарь */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <button onClick={goToPreviousMonth} className="text-gray-400 hover:text-gray-600">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <h2 className="text-lg font-semibold">
              {(() => {
                const label = format(selectedDate, 'LLLL yyyy', { locale: ru })
                return label.charAt(0).toUpperCase() + label.slice(1)
              })()}
            </h2>
            <button onClick={goToNextMonth} className="text-gray-400 hover:text-gray-600">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>

          {/* Дни недели */}
          <div className="grid grid-cols-7 gap-1 mb-2">
            {['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'].map(day => (
              <div key={day} className="text-center text-xs text-gray-500 py-2">
                {day}
              </div>
            ))}
          </div>

          {/* Календарная сетка */}
          <div className="grid grid-cols-7 gap-1">
            {calendarDays.map((day, index) => (
              <div key={index} className="aspect-square flex items-center justify-center">
                {day && (() => {
                  const dateStr = format(day, 'yyyy-MM-dd')
                  const color = monthMoodMap[dateStr] || ''
                  return (
                    <button
                      className={`calendar-day ${isToday(day) ? 'today' : ''} ${color}`}
                      onClick={() => handleDateSelect(day)}
                    >
                      {format(day, 'd')}
                    </button>
                  )
                })()}
              </div>
            ))}
          </div>
        </div>

        {/* Записи за выбранный день */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">
            {format(selectedDate, 'd MMMM yyyy г.', { locale: ru })}
          </h3>

          {loading && <div className="text-center text-gray-500">Загрузка...</div>}

          {!loading && (
            <>
              {/* Если есть заметки - показываем их */}
              {notes.length > 0 ? (
                <div className="space-y-3">
                  {notes.map(note => (
                    editingNote && editingNote.id === note.id ? (
                      <div key={note.id} className="bg-gray-50 rounded-xl p-3">
                        <div className="space-y-4">
                          <div className="flex items-center gap-3">
                            <select
                              value={editMood}
                              onChange={(e) => setEditMood(e.target.value)}
                              className="bg-gray-100 rounded-lg px-3 py-2 text-sm border-none outline-none focus:ring-2 focus:ring-blue-500"
                            >
                              <option value="" disabled>Выберите настроение</option>
                              {MOOD_OPTIONS.map((m) => (
                                <option key={m.value} value={m.value}>{m.label}</option>
                              ))}
                            </select>
                            <span className="inline-flex"><MoodIcon value={editMood || 'neutral'} /></span>
                          </div>
                          <textarea
                            value={editContent}
                            onChange={e => setEditContent(e.target.value)}
                            className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                            placeholder="Измените заметку..."
                            rows={4}
                          />
                          <div className="flex gap-3">
                            <button onClick={saveEdit} disabled={!editMood} className="btn flex-1 disabled:opacity-50">
                              Сохранить
                            </button>
                            <button onClick={cancelEdit} className="btn-secondary flex-1">
                              Отмена
                            </button>
                          </div>
                        </div>
                      </div >
                    ) : (
                      <div key={note.id} className="bg-gray-50 rounded-xl p-3">
                        <div className="flex items-start gap-3">
                          <span className="inline-flex">
                            <MoodIcon value={normalizeMood(note.mood || 'neutral')} />
                          </span>
                          <div className="flex-1">
                            <div className="text-sm text-gray-500 mb-1">
                              {format(new Date(note.created_at), 'HH:mm')}
                            </div>
                            <div className="text-sm">{note.content}</div>
                          </div>
                          <button onClick={() => startEdit(note)} className="text-gray-400 hover:text-gray-600">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                              <path d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13M18.5 2.5C18.8978 2.10218 19.4374 1.87868 20 1.87868C20.5626 1.87868 21.1022 2.10218 21.5 2.5C21.8978 2.89782 22.1213 3.43739 22.1213 4C22.1213 4.56261 21.8978 5.10218 21.5 5.5L12 15L8 11L18.5 2.5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    )
                  ))
                  }
                </div >
              ) : showCreateForm ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <select
                      value={selectedMood}
                      onChange={(e) => setSelectedMood(e.target.value)}
                      className="bg-gray-100 rounded-lg px-3 py-2 text-sm border-none outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="" disabled>Выберите настроение</option>
                      {MOOD_OPTIONS.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <textarea
                    value={newNote}
                    onChange={e => setNewNote(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                    placeholder="Напишите заметку..."
                    rows={4}
                  />

                  <div className="flex gap-3">
                    <button
                      onClick={createNote}
                      disabled={!selectedMood}
                      className="btn flex-1 flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <path d="M19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H16L21 8V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      Сохранить
                    </button>
                    <button
                      onClick={cancelCreate}
                      className="btn-secondary flex-1 flex items-center justify-center gap-2"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      Отмена
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <div className="text-6xl mb-4">📖</div>
                  <div className="text-lg font-medium text-gray-700 mb-2">Нет записей</div>
                  <button
                    onClick={() => setShowCreateForm(true)}
                    className="btn"
                  >
                    Создать запись
                  </button>
                </div >
              )
              }
            </>
          )}
        </div >
      </div >
    </div >
  )
}

// Компонент загрузочного экрана
function LoadingScreen({ progress = 0 }) {
  return (
    <div className="fixed inset-0 bg-gray-50 flex flex-col items-center justify-center z-50">
      <div className="w-full max-w-sm px-8">
        {/* Иконка бегущего человека */}
        <div className="flex justify-center mb-8 relative">
          <svg
            width="80"
            height="80"
            viewBox="0 0 100 100"
            className="text-yellow-500"
            style={{
              animation: 'bounce 1s ease-in-out infinite'
            }}
          >
            {/* Голова */}
            <circle cx="50" cy="18" r="9" fill="currentColor" />
            {/* Тело */}
            <rect x="47" y="27" width="6" height="18" rx="3" fill="currentColor" />
            {/* Левая рука (поднята вверх и согнута) */}
            <path
              d="M47 32 L42 25 L40 28 L45 35"
              fill="currentColor"
            />
            {/* Правая рука (поднята вверх и согнута) */}
            <path
              d="M53 32 L58 25 L60 28 L55 35"
              fill="currentColor"
            />
            {/* Левая нога (в движении вперед) */}
            <path
              d="M47 45 L44 58 L42 62 L46 60"
              fill="currentColor"
            />
            {/* Правая нога (в движении назад) */}
            <path
              d="M53 45 L56 58 L58 62 L54 60"
              fill="currentColor"
            />
          </svg>
        </div>

        {/* Прогресс-бар */}
        <div className="relative w-full h-4 bg-gray-200 rounded-full overflow-hidden shadow-lg mb-4" style={{
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06), 0 0 0 1px rgba(255, 255, 255, 0.5)'
        }}>
          {/* Тень под прогресс-баром */}
          <div className="absolute inset-0 bg-gray-300 rounded-full transform translate-x-1 translate-y-1 opacity-30"></div>

          {/* Заполненная часть */}
          <div
            className="absolute left-0 top-0 h-full bg-yellow-500 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />

          {/* Незаполненная часть */}
          <div
            className="absolute right-0 top-0 h-full bg-gray-300 rounded-full"
            style={{ width: `${100 - progress}%` }}
          />
        </div>

        {/* Текст */}
        <p className="text-center text-gray-600 text-sm font-medium uppercase tracking-wide">
          I'M MAKING PROGRESS...
        </p>
      </div>
    </div>
  )
}

// Нижняя навигация
function BottomNavigation({ active, onNavigate }) {
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100">
      <div className="flex justify-around py-2">
        <button
          className={`nav-item ${active === 'tasks' ? 'active' : 'inactive'}`}
          onClick={() => onNavigate('tasks')}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-xs font-medium">Задачи</span>
        </button>

        <button
          className={`nav-item ${active === 'statistics' ? 'active' : 'inactive'}`}
          onClick={() => onNavigate('statistics')}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M3 3V21H21M7 16L12 11L16 15L21 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-xs font-medium">Статистика</span>
        </button>

        <button
          className={`nav-item ${active === 'journal' ? 'active' : 'inactive'}`}
          onClick={() => onNavigate('journal')}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M4 19.5C4 18.1193 5.11929 17 6.5 17H20M4 19.5C4 20.8807 5.11929 22 6.5 22H20M4 19.5V5C4 3.89543 4.89543 3 6 3H18C19.1046 3 20 3.89543 20 5V19.5M8 7H16M8 11H12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-xs font-medium">Журнал</span>
        </button>
      </div>
    </div>
  )
}

// Главный компонент приложения
export default function App() {
  const tg = useTelegram()
  const initData = useInitData()
  const [route, setRoute] = useState('tasks')
  const [showCreateTask, setShowCreateTask] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [showCreateSubtask, setShowCreateSubtask] = useState(false)
  const [parentTaskForSubtask, setParentTaskForSubtask] = useState(null)
  const [editingSubtask, setEditingSubtask] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [preloadedNotes, setPreloadedNotes] = useState([])
  const [preloadedMonthMoodMap, setPreloadedMonthMoodMap] = useState({})
  const progressRef = useRef(0)

  const api = useMemo(() => createApiClient(initData), [initData])

  // Загрузка всех данных при старте приложения
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setIsLoading(true)
        setLoadingProgress(0)
        progressRef.current = 0

        // Функция для плавного увеличения прогресса
        const animateProgress = (targetProgress, duration = 500) => {
          return new Promise((resolve) => {
            const startProgress = progressRef.current
            const startTime = Date.now()

            const updateProgress = () => {
              const elapsed = Date.now() - startTime
              const progress = Math.min(
                startProgress + (targetProgress - startProgress) * (elapsed / duration),
                targetProgress
              )
              progressRef.current = progress
              setLoadingProgress(progress)

              if (progress < targetProgress) {
                requestAnimationFrame(updateProgress)
              } else {
                progressRef.current = targetProgress
                setLoadingProgress(targetProgress)
                resolve()
              }
            }

            requestAnimationFrame(updateProgress)
          })
        }

        // Загружаем данные последовательно с плавной анимацией прогресса
        try {
          // 1. Задачи для сегодня
          const dateStr = formatDateForAPI(new Date())
          await api(`/tasks?date=${dateStr}`)
          await animateProgress(20)
        } catch (error) {
          console.error('Error loading tasks:', error)
          await animateProgress(20)
        }

        try {
          // 2. Статистика
          await api('/stats?period=day')
          await animateProgress(40)
        } catch (error) {
          console.error('Error loading stats:', error)
          await animateProgress(40)
        }

        try {
          // 3. Привычки
          await api('/habits')
          await animateProgress(60)
        } catch (error) {
          console.error('Error loading habits:', error)
          await animateProgress(60)
        }

        try {
          // 4. Заметки для сегодня
          const today = new Date()
          const dateStr = format(today, 'yyyy-MM-dd')
          const notesData = await api(`/notes?date=${dateStr}`)
          setPreloadedNotes(Array.isArray(notesData) ? notesData : [])
          await animateProgress(80)
        } catch (error) {
          console.error('Error loading notes:', error)
          await animateProgress(80)
        }

        try {
          // 5. Заметки за текущий месяц для календаря
          const today = new Date()
          const year = today.getFullYear()
          const month = today.getMonth() + 1
          const monthNotesData = await api(`/notes?year=${year}&month=${month}`)

          // Создаем карту настроений из предзагруженных данных
          const map = {}
          if (Array.isArray(monthNotesData)) {
            const notesByDate = {}
            monthNotesData.forEach(note => {
              if (note.date && !notesByDate[note.date]) {
                notesByDate[note.date] = note
              }
            })

            // Функция для преобразования настроения в классы
            const moodToClasses = (mood) => {
              const m = mood === '😡' ? 'very_bad' :
                mood === '😞' ? 'bad' :
                  mood === '😐' ? 'neutral' :
                    mood === '🙂' ? 'good' :
                      mood === '🤩' ? 'very_good' : mood
              switch (m) {
                case 'very_good': return 'bg-green-600 text-white'
                case 'good': return 'bg-green-300 text-gray-900'
                case 'neutral': return 'bg-yellow-300 text-gray-900'
                case 'bad': return 'bg-red-300 text-gray-900'
                case 'very_bad': return 'bg-red-600 text-white'
                default: return ''
              }
            }

            Object.entries(notesByDate).forEach(([dateStr, note]) => {
              if (note?.mood) {
                map[dateStr] = moodToClasses(note.mood)
              }
            })
          }
          setPreloadedMonthMoodMap(map)
          await animateProgress(100)
        } catch (error) {
          console.error('Error loading month notes:', error)
          await animateProgress(100)
        }

        // Небольшая задержка перед скрытием экрана загрузки
        await new Promise(resolve => setTimeout(resolve, 300))

        setIsLoading(false)
      } catch (error) {
        console.error('Error loading initial data:', error)
        setIsLoading(false)
      }
    }

    if (initData) {
      loadInitialData()
    } else {
      // Если нет initData, все равно скрываем загрузку через небольшую задержку
      setTimeout(() => setIsLoading(false), 500)
    }
  }, [api, initData])

  useEffect(() => {
    // В DEV режиме может не быть Telegram WebApp
    if (tg) {
      tg.ready()
      tg.expand()
    } else if (import.meta.env.DEV) {
      console.log('🔧 DEV mode: Telegram WebApp not available, running in local development mode')
    }
  }, [tg])

  const handleCreateTask = () => {
    setShowCreateTask(true)
    setEditingTask(null)
  }

  const handleEditTask = (task) => {
    setEditingTask(task)
    setShowCreateTask(true)
  }

  const taskUpdateCallbackRef = useRef(null)
  const [tasksPageKey, setTasksPageKey] = useState(0) // Ключ для принудительного обновления

  const handleTaskCreated = () => {
    setShowCreateTask(false)
    setEditingTask(null)
    setRoute('tasks')
    // Принудительно обновляем страницу задач через изменение ключа
    setTasksPageKey(prev => prev + 1)
  }

  const handleBack = () => {
    setShowCreateTask(false)
    setEditingTask(null)
  }

  const handleCreateSubtask = (task) => {
    setParentTaskForSubtask(task)
    setEditingSubtask(null)
    setShowCreateSubtask(true)
  }

  const handleEditSubtask = (subtask, parentTask) => {
    setEditingSubtask(subtask)
    setParentTaskForSubtask(parentTask)
    setShowCreateSubtask(true)
  }

  const handleSubtaskCreated = () => {
    setShowCreateSubtask(false)
    setParentTaskForSubtask(null)
    setEditingSubtask(null)
    setRoute('tasks')
    setTasksPageKey(prev => prev + 1)
  }

  const handleBackSubtask = () => {
    setShowCreateSubtask(false)
    setParentTaskForSubtask(null)
    setEditingSubtask(null)
  }

  // Показываем загрузочный экран пока данные не загружены
  if (isLoading) {
    return <LoadingScreen progress={loadingProgress} />
  }

  if (showCreateSubtask) {
    return <CreateSubtaskPage onBack={handleBackSubtask} onSubtaskCreated={handleSubtaskCreated} parentTask={parentTaskForSubtask} subtask={editingSubtask} />
  }

  if (showCreateTask) {
    return <CreateTaskPage onBack={handleBack} onTaskCreated={handleTaskCreated} task={editingTask} />
  }

  return (
    <div>
      {route === 'tasks' ? (
        <TasksPage
          key={tasksPageKey}
          onCreateTask={handleCreateTask}
          onEditTask={handleEditTask}
          onCreateSubtask={handleCreateSubtask}
          onEditSubtask={handleEditSubtask}
          onTaskUpdated={(callback) => {
            taskUpdateCallbackRef.current = callback
          }}
        />
      ) : route === 'statistics' ? (
        <StatisticsPage />
      ) : (
        <JournalPage
          preloadedNotes={preloadedNotes}
          preloadedMonthMoodMap={preloadedMonthMoodMap}
        />
      )}
      <BottomNavigation active={route} onNavigate={setRoute} />
    </div>
  )
}