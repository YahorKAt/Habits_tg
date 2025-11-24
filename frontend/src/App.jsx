import React, { useEffect, useMemo, useState, useRef } from 'react'

// Импорты утилит и хуков
import { createApiClient } from './utils/api.js'
import { useInitData, useTelegram } from './hooks/useTelegram.js'

// Импорты компонентов
import TaskForm from './components/TaskForm.jsx'
import SubtaskForm from './components/SubtaskForm.jsx'
import BottomNavigation from './components/BottomNavigation.jsx'

// Импорты страниц
import TasksPage from './pages/TasksPage.jsx'
import StatisticsPage from './pages/StatisticsPage.jsx'
import JournalPage from './pages/JournalPage.jsx'

// Используем TaskForm как CreateTaskPage для обратной совместимости
const CreateTaskPage = TaskForm

// Используем SubtaskForm как CreateSubtaskPage для обратной совместимости
const CreateSubtaskPage = SubtaskForm

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

  const api = useMemo(() => createApiClient(initData), [initData])

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

  const handleTaskCreated = (taskData, isEdit = false) => {
    setShowCreateTask(false)
    setEditingTask(null)
    setRoute('tasks')

    if (isEdit) {
      // При редактировании обновляем только эту задачу через колбэк
      if (taskUpdateCallbackRef.current) {
        taskUpdateCallbackRef.current(taskData)
      }
    } else {
      // При создании новой задачи обновляем весь список через изменение ключа
      setTasksPageKey(prev => prev + 1)
    }
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
        <JournalPage />
      )}
      <BottomNavigation active={route} onNavigate={setRoute} />
    </div>
  )
}
