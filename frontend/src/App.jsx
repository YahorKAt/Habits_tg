import React, { useEffect, useMemo, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Константы для групп задач
const TASK_CATEGORIES = {
  general: { name: 'Общее', icon: '📋' },
  sport: { name: 'Спорт', icon: '🏋️' },
  study: { name: 'Учёба', icon: '📚' },
  work: { name: 'Работа', icon: '💼' },
}

function useTelegram() {
  const tg = window.Telegram?.WebApp
  return tg
}

function useInitData() {
  const tg = useTelegram()
  const initData = tg?.initData || ''
  return initData
}

function Header({ onNavigate, active, onBack, isEditing }) {
  return (
    <div className="sticky top-0 z-10 backdrop-blur bg-white/70 dark:bg-gray-900/70">
      <div className="max-w-xl mx-auto px-4 py-3 flex items-center justify-between">
        {onBack ? (
          <>
            <button onClick={onBack} className="text-blue-600 hover:text-blue-700 dark:text-blue-400">
              ← Назад
            </button>
            <h1 className="text-xl font-semibold">{isEditing ? 'Редактировать задачу' : 'Создать задачу'}</h1>
            <div></div>
          </>
        ) : (
          <>
            <h1 className="text-xl font-semibold">Habits</h1>
            <div></div>
          </>
        )}
      </div>
    </div>
  )
}

function TaskItem({ task, onToggleTask, onToggleSubtask, onDelete, onEdit }) {
  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('ru-RU')
  }

  const getRepeatText = () => {
    if (task.repeat_type === 'NONE') return ''
    const interval = task.repeat_interval
    switch (task.repeat_type) {
      case 'DAILY': return `Каждый ${interval > 1 ? interval : ''} день`
      case 'WEEKLY': return `Каждую ${interval > 1 ? interval : ''} неделю`
      case 'MONTHLY': return `Каждый ${interval > 1 ? interval : ''} месяц`
      case 'CUSTOM': return 'По расписанию'
      default: return ''
    }
  }

  return (
    <div className="card animate-fadeInUp">
      <div className="flex items-center gap-3">
        <input type="checkbox" checked={task.completed} onChange={() => onToggleTask(task)} />
        <div className={`flex-1 ${task.completed ? 'line-through opacity-60' : ''}`}>
          <div className="flex items-center gap-2">
            <span className="text-lg">{TASK_CATEGORIES[task.category]?.icon || TASK_CATEGORIES.general.icon}</span>
            <span>{task.title}</span>
          </div>
          {task.repeat_type !== 'NONE' && (
            <div className="text-sm text-blue-600 dark:text-blue-400 mt-1">
              {getRepeatText()}
              {task.next_due_date && (
                <span className="ml-2 text-gray-500">
                  Следующая: {formatDate(task.next_due_date)}
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <button onClick={() => onEdit(task)} className="text-blue-500 hover:text-blue-600">✏️</button>
          <button onClick={() => onDelete(task)} className="text-red-500 hover:text-red-600">✕</button>
        </div>
      </div>
      <div className="mt-2 pl-7 space-y-2">
        {task.subtasks?.map(st => (
          <div key={st.id} className="flex items-center gap-3">
            <input type="checkbox" checked={st.completed} onChange={() => onToggleSubtask(task, st)} />
            <div className={`flex-1 ${st.completed ? 'line-through opacity-60' : ''}`}>{st.title}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CreateTask({ onBack, onTaskCreated }) {
  const initData = useInitData()
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('general')
  const [repeatType, setRepeatType] = useState('NONE')
  const [repeatInterval, setRepeatInterval] = useState(1)
  const [customDate, setCustomDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [subtasks, setSubtasks] = useState([])
  const [newSubtask, setNewSubtask] = useState('')
  const [loading, setLoading] = useState(false)

  async function api(path, options = {}) {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData,
        ...(options.headers || {})
      }
    })
    if (!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  const addSubtask = () => {
    if (!newSubtask.trim()) return
    setSubtasks([...subtasks, { id: Date.now(), title: newSubtask.trim() }])
    setNewSubtask('')
  }

  const removeSubtask = (id) => {
    setSubtasks(subtasks.filter(st => st.id !== id))
  }

  const createTask = async () => {
    if (!title.trim()) return

    setLoading(true)
    try {
      let nextDueDate = null
      let endDateValue = null

      if (repeatType !== 'NONE') {
        if (repeatType === 'CUSTOM' && customDate) {
          nextDueDate = new Date(customDate).toISOString()
        } else if (repeatType !== 'CUSTOM') {
          // Автоматически вычисляем следующую дату
          const now = new Date()
          if (repeatType === 'DAILY') {
            nextDueDate = new Date(now.getTime() + repeatInterval * 24 * 60 * 60 * 1000).toISOString()
          } else if (repeatType === 'WEEKLY') {
            nextDueDate = new Date(now.getTime() + repeatInterval * 7 * 24 * 60 * 60 * 1000).toISOString()
          } else if (repeatType === 'MONTHLY') {
            nextDueDate = new Date(now.getTime() + repeatInterval * 30 * 24 * 60 * 60 * 1000).toISOString()
          }
        }

        if (endDate) {
          endDateValue = new Date(endDate).toISOString()
        }
      }

      // Создаем задачу
      const task = await api('/task', {
        method: 'POST',
        body: JSON.stringify({
          title: title.trim(),
          category: category,
          repeat_type: repeatType,
          repeat_interval: repeatInterval,
          next_due_date: nextDueDate,
          end_date: endDateValue
        })
      })

      // Создаем подзадачи
      for (const subtask of subtasks) {
        await api('/subtask', {
          method: 'POST',
          body: JSON.stringify({
            task_id: task.id,
            title: subtask.title
          })
        })
      }

      onTaskCreated()
    } catch (error) {
      console.error('Error creating task:', error)
      alert('Ошибка при создании задачи')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto p-4 space-y-4">
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Новая задача</h2>

        <div className="space-y-4">
          {/* Название задачи */}
          <div>
            <label className="block text-sm font-medium mb-2">Название задачи *</label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="input"
              placeholder="Введите название задачи"
              required
            />
          </div>

          {/* Группа задачи */}
          <div>
            <label className="block text-sm font-medium mb-2">Группа задачи</label>
            <select value={category} onChange={e => setCategory(e.target.value)} className="input">
              {Object.entries(TASK_CATEGORIES).map(([key, value]) => (
                <option key={key} value={key}>{value.name}</option>
              ))}
            </select>
          </div>

          {/* Тип повторения */}
          <div>
            <label className="block text-sm font-medium mb-2">Повторение</label>
            <select value={repeatType} onChange={e => setRepeatType(e.target.value)} className="input">
              <option value="NONE">Без повторения</option>
              <option value="DAILY">Ежедневно</option>
              <option value="WEEKLY">Еженедельно</option>
              <option value="MONTHLY">Ежемесячно</option>
              <option value="CUSTOM">По расписанию</option>
            </select>
          </div>

          {/* Интервал */}
          {repeatType !== 'NONE' && repeatType !== 'CUSTOM' && (
            <div>
              <label className="block text-sm font-medium mb-2">Интервал</label>
              <input
                type="number"
                min="1"
                value={repeatInterval}
                onChange={e => setRepeatInterval(parseInt(e.target.value) || 1)}
                className="input"
                placeholder="Каждые N дней/недель/месяцев"
              />
            </div>
          )}

          {/* Кастомная дата */}
          {repeatType === 'CUSTOM' && (
            <div>
              <label className="block text-sm font-medium mb-2">Дата следующего выполнения</label>
              <input
                type="datetime-local"
                value={customDate}
                onChange={e => setCustomDate(e.target.value)}
                className="input"
              />
            </div>
          )}

          {/* Дата окончания */}
          {repeatType !== 'NONE' && (
            <div>
              <label className="block text-sm font-medium mb-2">Дата окончания (необязательно)</label>
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className="input"
              />
            </div>
          )}

          {/* Подзадачи */}
          <div>
            <label className="block text-sm font-medium mb-2">Подзадачи</label>
            <div className="space-y-2">
              {subtasks.map(subtask => (
                <div key={subtask.id} className="flex items-center gap-2">
                  <span className="flex-1 text-sm">• {subtask.title}</span>
                  <button
                    onClick={() => removeSubtask(subtask.id)}
                    className="text-red-500 hover:text-red-600 text-sm"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  value={newSubtask}
                  onChange={e => setNewSubtask(e.target.value)}
                  className="input flex-1"
                  placeholder="Добавить подзадачу"
                  onKeyPress={e => e.key === 'Enter' && addSubtask()}
                />
                <button onClick={addSubtask} className="btn !px-3 !py-2">+</button>
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={onBack} className="btn !bg-gray-500 hover:!bg-gray-600 flex-1">
            Отмена
          </button>
          <button
            onClick={createTask}
            disabled={!title.trim() || loading}
            className="btn flex-1"
          >
            {loading ? 'Создание...' : 'Создать задачу'}
          </button>
        </div>
      </div>
    </div>
  )
}

function EditTask({ task, onBack, onTaskUpdated }) {
  const initData = useInitData()
  const [title, setTitle] = useState(task.title)
  const [category, setCategory] = useState(task.category || 'general')
  const [repeatType, setRepeatType] = useState(task.repeat_type || 'NONE')
  const [repeatInterval, setRepeatInterval] = useState(task.repeat_interval || 1)
  const [customDate, setCustomDate] = useState(task.next_due_date ? new Date(task.next_due_date).toISOString().slice(0, 16) : '')
  const [endDate, setEndDate] = useState(task.end_date ? new Date(task.end_date).toISOString().split('T')[0] : '')
  const [subtasks, setSubtasks] = useState(task.subtasks || [])
  const [newSubtask, setNewSubtask] = useState('')
  const [loading, setLoading] = useState(false)

  async function api(path, options = {}) {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData,
        ...(options.headers || {})
      }
    })
    if (!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  const addSubtask = () => {
    if (!newSubtask.trim()) return
    setSubtasks([...subtasks, { id: Date.now(), title: newSubtask.trim() }])
    setNewSubtask('')
  }

  const removeSubtask = (id) => {
    setSubtasks(subtasks.filter(st => st.id !== id))
  }

  const updateTask = async () => {
    if (!title.trim()) return

    setLoading(true)
    try {
      let nextDueDate = null
      let endDateValue = null

      if (repeatType !== 'NONE') {
        if (repeatType === 'CUSTOM' && customDate) {
          nextDueDate = new Date(customDate).toISOString()
        } else if (repeatType !== 'CUSTOM') {
          // Автоматически вычисляем следующую дату
          const now = new Date()
          if (repeatType === 'DAILY') {
            nextDueDate = new Date(now.getTime() + repeatInterval * 24 * 60 * 60 * 1000).toISOString()
          } else if (repeatType === 'WEEKLY') {
            nextDueDate = new Date(now.getTime() + repeatInterval * 7 * 24 * 60 * 60 * 1000).toISOString()
          } else if (repeatType === 'MONTHLY') {
            nextDueDate = new Date(now.getTime() + repeatInterval * 30 * 24 * 60 * 60 * 1000).toISOString()
          }
        }

        if (endDate) {
          endDateValue = new Date(endDate).toISOString()
        }
      }

      // Обновляем задачу
      const updatedTask = await api(`/task/${task.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          title: title.trim(),
          category: category,
          repeat_type: repeatType,
          repeat_interval: repeatInterval,
          next_due_date: nextDueDate,
          end_date: endDateValue
        })
      })

      // Удаляем все существующие подзадачи
      for (const subtask of task.subtasks || []) {
        await api(`/subtask/${subtask.id}`, { method: 'DELETE' })
      }

      // Создаем новые подзадачи
      for (const subtask of subtasks) {
        await api('/subtask', {
          method: 'POST',
          body: JSON.stringify({
            task_id: task.id,
            title: subtask.title
          })
        })
      }

      onTaskUpdated()
    } catch (error) {
      console.error('Error updating task:', error)
      alert('Ошибка при обновлении задачи')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto p-4 space-y-4">
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Редактировать задачу</h2>

        <div className="space-y-4">
          {/* Название задачи */}
          <div>
            <label className="block text-sm font-medium mb-2">Название задачи *</label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="input"
              placeholder="Введите название задачи"
              required
            />
          </div>

          {/* Группа задачи */}
          <div>
            <label className="block text-sm font-medium mb-2">Группа задачи</label>
            <select value={category} onChange={e => setCategory(e.target.value)} className="input">
              {Object.entries(TASK_CATEGORIES).map(([key, value]) => (
                <option key={key} value={key}>{value.name}</option>
              ))}
            </select>
          </div>

          {/* Тип повторения */}
          <div>
            <label className="block text-sm font-medium mb-2">Повторение</label>
            <select value={repeatType} onChange={e => setRepeatType(e.target.value)} className="input">
              <option value="NONE">Без повторения</option>
              <option value="DAILY">Ежедневно</option>
              <option value="WEEKLY">Еженедельно</option>
              <option value="MONTHLY">Ежемесячно</option>
              <option value="CUSTOM">По расписанию</option>
            </select>
          </div>

          {/* Интервал */}
          {repeatType !== 'NONE' && repeatType !== 'CUSTOM' && (
            <div>
              <label className="block text-sm font-medium mb-2">Интервал</label>
              <input
                type="number"
                min="1"
                value={repeatInterval}
                onChange={e => setRepeatInterval(parseInt(e.target.value) || 1)}
                className="input"
                placeholder="Каждые N дней/недель/месяцев"
              />
            </div>
          )}

          {/* Кастомная дата */}
          {repeatType === 'CUSTOM' && (
            <div>
              <label className="block text-sm font-medium mb-2">Дата следующего выполнения</label>
              <input
                type="datetime-local"
                value={customDate}
                onChange={e => setCustomDate(e.target.value)}
                className="input"
              />
            </div>
          )}

          {/* Дата окончания */}
          {repeatType !== 'NONE' && (
            <div>
              <label className="block text-sm font-medium mb-2">Дата окончания (необязательно)</label>
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className="input"
              />
            </div>
          )}

          {/* Подзадачи */}
          <div>
            <label className="block text-sm font-medium mb-2">Подзадачи</label>
            <div className="space-y-2">
              {subtasks.map(subtask => (
                <div key={subtask.id} className="flex items-center gap-2">
                  <span className="flex-1 text-sm">• {subtask.title}</span>
                  <button
                    onClick={() => removeSubtask(subtask.id)}
                    className="text-red-500 hover:text-red-600 text-sm"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  value={newSubtask}
                  onChange={e => setNewSubtask(e.target.value)}
                  className="input flex-1"
                  placeholder="Добавить подзадачу"
                  onKeyPress={e => e.key === 'Enter' && addSubtask()}
                />
                <button onClick={addSubtask} className="btn !px-3 !py-2">+</button>
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={onBack} className="btn !bg-gray-500 hover:!bg-gray-600 flex-1">
            Отмена
          </button>
          <button
            onClick={updateTask}
            disabled={!title.trim() || loading}
            className="btn flex-1"
          >
            {loading ? 'Сохранение...' : 'Сохранить изменения'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Tasks({ onCreateTask, onEditTask }) {
  const initData = useInitData()
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState([])

  async function api(path, options = {}) {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData,
        ...(options.headers || {})
      }
    })
    if (!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  const load = async () => {
    setLoading(true)
    try {
      const data = await api('/tasks')
      setItems(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const deleteTask = async (task) => {
    await api(`/task/${task.id}`, { method: 'DELETE' })
    setItems(prev => prev.filter(t => t.id !== task.id))
  }

  const toggleTask = async (task) => {
    const updated = await api(`/task/${task.id}/complete`, { method: 'POST' })
    setItems(prev => prev.map(t => t.id === task.id ? updated : t))
  }

  const toggleSubtask = async (task, st) => {
    const updated = await api(`/subtask/${st.id}/complete`, { method: 'POST' })
    setItems(prev => prev.map(t => t.id === task.id ? { ...t, subtasks: t.subtasks.map(s => s.id === st.id ? updated : s) } : t))
  }

  const handleEditTask = (task) => {
    onEditTask(task, load) // Передаем функцию load для обновления списка
  }

  return (
    <div className="max-w-xl mx-auto p-4 pb-24 space-y-3">
      <div className="card">
        <div className="flex justify-center items-center">
          {/* <h2 className="text-lg font-semibold">Мои задачи</h2> */}
          <button onClick={onCreateTask} className="btn">
            + Добавить задачу
          </button>
        </div>
      </div>

      {loading && <div className="text-center opacity-70">Loading...</div>}
      <div className="space-y-3">
        {items.map(task => (
          <TaskItem key={task.id} task={task} onToggleTask={toggleTask} onToggleSubtask={toggleSubtask} onDelete={deleteTask} onEdit={handleEditTask} />
        ))}
      </div>
    </div>
  )
}

function Stats() {
  const initData = useInitData()
  const [period, setPeriod] = useState('7')
  const [stats, setStats] = useState(null)

  async function api(path) {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { 'X-Telegram-Init-Data': initData }
    })
    if (!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  const load = async (p) => {
    const data = await api(`/stats?period=${p}`)
    setStats(data)
  }

  useEffect(() => { load(period) }, [period])

  return (
    <div className="max-w-xl mx-auto p-4 pb-24">
      <div className="card">
        <div className="flex gap-2 mb-3">
          {['7', '30', 'all'].map(p => (
            <button key={p} className={`btn !px-3 !py-1.5 ${period === p ? '!bg-blue-700' : ''}`} onClick={() => setPeriod(p)}>
              {p === 'all' ? 'All' : `${p}d`}
            </button>
          ))}
        </div>
        {stats && (
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="card"><div className="text-sm opacity-70">Tasks</div><div className="text-2xl font-semibold">{stats.tasks_completed}</div></div>
            <div className="card"><div className="text-sm opacity-70">Subtasks</div><div className="text-2xl font-semibold">{stats.subtasks_completed}</div></div>
            <div className="card"><div className="text-2xl font-semibold">{stats.total_completed}</div></div>
          </div>
        )}
      </div>
    </div>
  )
}

function Notes() {
  const initData = useInitData()
  const [notes, setNotes] = useState([])
  const [newNote, setNewNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentDate] = useState(new Date().toISOString().split('T')[0])

  async function api(path, options = {}) {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData,
        ...(options.headers || {})
      }
    })
    if (!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  const loadNotes = async () => {
    setLoading(true)
    try {
      const data = await api(`/notes?date=${currentDate}`)
      setNotes(data)
    } catch (error) {
      console.error('Error loading notes:', error)
      setNotes([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNotes()
  }, [currentDate])

  const addNote = async () => {
    if (!newNote.trim()) return

    try {
      const note = await api('/notes', {
        method: 'POST',
        body: JSON.stringify({
          content: newNote.trim(),
          date: currentDate
        })
      })
      setNotes(prev => [note, ...prev])
      setNewNote('')
    } catch (error) {
      console.error('Error adding note:', error)
      alert('Ошибка при добавлении заметки')
    }
  }

  const deleteNote = async (noteId) => {
    try {
      await api(`/notes/${noteId}`, { method: 'DELETE' })
      setNotes(prev => prev.filter(n => n.id !== noteId))
    } catch (error) {
      console.error('Error deleting note:', error)
      alert('Ошибка при удалении заметки')
    }
  }

  const formatTime = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="max-w-xl mx-auto p-4 pb-24 space-y-4">
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Ежедневные заметки</h2>
        <div className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          {new Date(currentDate).toLocaleDateString('ru-RU', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
          })}
        </div>

        <div className="space-y-3">
          <div className="flex gap-2">
            <input
              value={newNote}
              onChange={e => setNewNote(e.target.value)}
              className="input flex-1"
              placeholder="Напишите вашу мысль..."
              onKeyPress={e => e.key === 'Enter' && addNote()}
            />
            <button
              onClick={addNote}
              disabled={!newNote.trim()}
              className="btn !px-4"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {loading && <div className="text-center opacity-70">Загрузка...</div>}

      <div className="space-y-3">
        {notes.map(note => (
          <div key={note.id} className="card animate-fadeInUp">
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <div className="whitespace-pre-wrap">{note.content}</div>
                <div className="text-xs text-gray-500 mt-2">
                  {formatTime(note.created_at)}
                </div>
              </div>
              <button
                onClick={() => deleteNote(note.id)}
                className="text-red-500 hover:text-red-600 text-sm"
              >
                ✕
              </button>
            </div>
          </div>
        ))}

        {notes.length === 0 && !loading && (
          <div className="text-center text-gray-500 dark:text-gray-400 py-8">
            <div className="text-4xl mb-2">📝</div>
            <div>Начните записывать ваши мысли</div>
          </div>
        )}
      </div>
    </div>
  )
}

function BottomNavigation({ active, onNavigate }) {
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 z-20">
      <div className="max-w-xl mx-auto px-4 py-3">
        <div className="flex justify-around">
          <button
            className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors ${active === 'tasks'
              ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/20'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
              }`}
            onClick={() => onNavigate('tasks')}
          >
            <span className="text-xl">📋</span>
            <span className="text-xs font-medium">Tasks</span>
          </button>

          <button
            className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors ${active === 'notes'
              ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/20'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
              }`}
            onClick={() => onNavigate('notes')}
          >
            <span className="text-xl">📝</span>
            <span className="text-xs font-medium">Notes</span>
          </button>

          <button
            className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors ${active === 'stats'
              ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/20'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
              }`}
            onClick={() => onNavigate('stats')}
          >
            <span className="text-xl">📊</span>
            <span className="text-xs font-medium">Profile</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const tg = useTelegram()
  const [route, setRoute] = useState('tasks')
  const [showCreateTask, setShowCreateTask] = useState(false)
  const [editingTask, setEditingTask] = useState(null)

  useEffect(() => {
    tg?.ready()
    tg?.expand()
    const theme = tg?.colorScheme
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [])

  const handleCreateTask = () => {
    setShowCreateTask(true)
  }

  const handleTaskCreated = () => {
    setShowCreateTask(false)
    setRoute('tasks')
  }

  const handleEditTask = (task, loadFunction) => {
    setEditingTask({ ...task, loadFunction })
  }

  const handleTaskUpdated = () => {
    if (editingTask && editingTask.loadFunction) {
      editingTask.loadFunction() // Перезагружаем список задач
    }
    setEditingTask(null)
    setRoute('tasks')
  }

  const handleBack = () => {
    setShowCreateTask(false)
    setEditingTask(null)
  }

  if (showCreateTask) {
    return (
      <div>
        <Header onBack={handleBack} isEditing={false} />
        <CreateTask onBack={handleBack} onTaskCreated={handleTaskCreated} />
      </div>
    )
  }

  if (editingTask) {
    const { loadFunction, ...taskData } = editingTask
    return (
      <div>
        <Header onBack={handleBack} isEditing={true} />
        <EditTask task={taskData} onBack={handleBack} onTaskUpdated={handleTaskUpdated} />
      </div>
    )
  }

  return (
    <div>
      <Header onNavigate={setRoute} active={route} />
      {route === 'tasks' ? (
        <Tasks onCreateTask={handleCreateTask} onEditTask={handleEditTask} />
      ) : route === 'notes' ? (
        <Notes />
      ) : (
        <Stats />
      )}
      <BottomNavigation active={route} onNavigate={setRoute} />
    </div>
  )
}




