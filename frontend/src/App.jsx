import React, { useEffect, useMemo, useState } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import { format, startOfWeek, addDays, isSameDay, isToday, startOfMonth, endOfMonth, eachDayOfInterval, getDay } from 'date-fns'
import { ru } from 'date-fns/locale'

const API_URL = import.meta.env.VITE_API_URL

// Константы для категорий задач
const TASK_CATEGORIES = {
  sport: { name: 'Спорт', icon: '🏆', color: '#EF4444' },
  study: { name: 'Учёба', icon: '🎓', color: '#3B82F6' },
  work: { name: 'Работа', icon: '💼', color: '#10B981' },
  personal: { name: 'Личное', icon: '👤', color: '#8B5CF6' },
}

const FREQUENCY_OPTIONS = [
  { value: 'daily', label: 'Ежедневно', description: 'Выполняется каждый день' },
  { value: 'weekly', label: 'Еженедельно', description: 'Выполняется раз в неделю' },
  { value: 'monthly', label: 'Ежемесячно', description: 'Выполняется раз в месяц' },
]

function useTelegram() {
  const tg = window.Telegram?.WebApp
  if (tg.initData) {
    console.log("Telegram initData found")
  } else {
    console.log("No Telegram data detected")
  }
  return tg
}

function useInitData() {
  const tg = useTelegram()
  const initData = tg?.initData || ''
  console.log("это данные пользователя initData =", initData)
  return initData
}

// Компонент для создания новой задачи
function CreateTaskPage({ onBack, onTaskCreated }) {
  const initData = useInitData()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('personal')
  const [frequency, setFrequency] = useState('daily')
  const [loading, setLoading] = useState(false)
  console.log("12345!!!это данные пользователя при создании задачи =", initData)
  async function api(path, options = {}) {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData,
        ...(options.headers || {})
      }
    })
    console.log("!!!!!это данные пользователя при создании задачи =", initData)
    if (!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  const createTask = async () => {
    if (!title.trim()) return

    setLoading(true)
    try {
      await api('/task', {
        method: 'POST',
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          category: category,
          frequency: frequency,
        })
      })

      onTaskCreated()
    } catch (error) {
      console.error('Error creating task:', error)
      alert('Ошибка при создании задачи')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white px-4 py-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="text-gray-600">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <h1 className="text-xl font-semibold">Новая задача</h1>
        </div>
        {/* <p className="text-gray-600 text-sm mt-1">Создайте задачу для отслеживания</p> */}
      </div>

      <div className="p-4 space-y-6">
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

        {/* Предварительный просмотр */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">Предварительный просмотр</label>
          <div className="card bg-gray-50 min-h-[100px] flex items-center justify-center text-gray-400">
            {title ? (
              <div className="text-center">
                <div className="text-lg mb-1">{TASK_CATEGORIES[category]?.icon}</div>
                <div className="font-medium">{title}</div>
                {description && <div className="text-sm text-gray-500 mt-1">{description}</div>}
              </div>
            ) : (
              'Предварительный просмотр появится здесь'
            )}
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
            {loading ? 'Создание...' : 'Создать задачу'}
          </button>
        </div>
      </div>
    </div>
  )
}

// Компонент для страницы задач
function TasksPage({ onCreateTask }) {
  const initData = useInitData()
  const [tasks, setTasks] = useState([])
  const [filter, setFilter] = useState('all')
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

  const loadTasks = async () => {
    setLoading(true)
    try {
      const data = await api('/tasks')
      setTasks(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
  }, [])

  const filteredTasks = useMemo(() => {
    switch (filter) {
      case 'active':
        return tasks.filter(task => !task.completed)
      case 'completed':
        return tasks.filter(task => task.completed)
      default:
        return tasks
    }
  }, [tasks, filter])

  const toggleTask = async (task) => {
    try {
      const updated = await api(`/task/${task.id}/complete`, { method: 'POST' })
      setTasks(prev => prev.map(t => t.id === task.id ? updated : t))
    } catch (error) {
      console.error('Error toggling task:', error)
    }
  }

  const deleteTask = async (task) => {
    try {
      await api(`/task/${task.id}`, { method: 'DELETE' })
      setTasks(prev => prev.filter(t => t.id !== task.id))
    } catch (error) {
      console.error('Error deleting task:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
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
              onClick={() => setFilter(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 pb-24 space-y-3">
        {loading && <div className="text-center text-gray-500">Загрузка...</div>}

        {filteredTasks.map(task => (
          <div key={task.id} className="task-card">
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={task.completed}
                onChange={() => toggleTask(task)}
                className="mt-1 w-5 h-5 rounded border-gray-300"
              />

              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">{TASK_CATEGORIES[task.category]?.icon || '📋'}</span>
                  <span className="text-sm bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                    {TASK_CATEGORIES[task.category]?.name || 'Общее'}
                  </span>
                  <span className="text-sm bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                    {task.frequency === 'daily' ? 'Ежедневно' :
                      task.frequency === 'weekly' ? 'Еженедельно' : 'Ежемесячно'}
                  </span>
                  <span className="text-sm bg-orange-500 text-white px-2 py-1 rounded-full flex items-center gap-1">
                    🔥 3
                  </span>
                </div>

                <h3 className={`font-medium ${task.completed ? 'line-through text-gray-500' : ''}`}>
                  {task.title}
                </h3>

                {task.description && (
                  <p className={`text-sm text-gray-500 mt-1 ${task.completed ? 'line-through' : ''}`}>
                    {task.description}
                  </p>
                )}

                {task.subtasks && task.subtasks.length > 0 && (
                  <p className="text-sm text-gray-500 mt-1">
                    {task.subtasks.filter(st => st.completed).length}/{task.subtasks.length} подзадач выполнено
                  </p>
                )}
              </div>

              <div className="flex gap-2">
                <button className="text-gray-400 hover:text-gray-600">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                <button className="text-gray-400 hover:text-gray-600">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                <button onClick={() => deleteTask(task)} className="text-red-400 hover:text-red-600">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M3 6H5H21M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        ))}

        {filteredTasks.length === 0 && !loading && (
          <div className="text-center text-gray-500 py-8">
            <div className="text-4xl mb-2">📋</div>
            <div>Нет задач</div>
          </div>
        )}
      </div>

      {/* Floating Action Button */}
      <button onClick={onCreateTask} className="floating-btn">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </div>
  )
}

// Компонент для страницы статистики
function StatisticsPage() {
  const initData = useInitData()
  const [period, setPeriod] = useState('week')
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)

  async function api(path) {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { 'X-Telegram-Init-Data': initData }
    })
    if (!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  const loadStats = async (p) => {
    setLoading(true)
    try {
      const data = await api(`/stats?period=${p}`)
      setStats(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStats(period)
  }, [period])

  // Данные для графика
  const chartData = [
    { name: 'Выполнено', value: 1, color: '#10B981' },
    { name: 'В процессе', value: 2, color: '#8B5CF6' },
    { name: 'Предстоящие', value: 0, color: '#3B82F6' },
  ]

  const totalTasks = chartData.reduce((sum, item) => sum + item.value, 0)
  const completedPercentage = totalTasks > 0 ? Math.round((chartData[0].value / totalTasks) * 100) : 0

  return (
    <div className="min-h-screen bg-gray-50">
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
              onChange={(e) => setPeriod(e.target.value)}
              className="bg-gray-100 rounded-lg px-3 py-1 text-sm"
            >
              <option value="week">Неделя</option>
              <option value="month">Месяц</option>
              <option value="year">Год</option>
            </select>
          </div>

          <div className="flex items-center gap-6">
            {/* График */}
            <div className="relative w-32 h-32">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={60}
                    paddingAngle={0}
                    dataKey="value"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <div className="text-2xl font-bold">{completedPercentage}%</div>
                  <div className="text-xs text-gray-500">Выполнено</div>
                </div>
              </div>
            </div>

            {/* Легенда */}
            <div className="space-y-2">
              {chartData.map((item, index) => (
                <div key={index} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm">{item.value} {item.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Расписание */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M8 2V5M16 2V5M3.5 9.09H20.5M21 8.5V17C21 18.1046 20.1046 19 19 19H5C3.89543 19 3 18.1046 3 17V8.5C3 7.39543 3.89543 6.5 5 6.5H19C20.1046 6.5 21 7.39543 21 8.5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <h2 className="text-lg font-semibold">Ваше расписание</h2>
            </div>
            <button className="text-gray-400 hover:text-gray-600">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13M18.5 2.5C18.8978 2.10218 19.4374 1.87868 20 1.87868C20.5626 1.87868 21.1022 2.10218 21.5 2.5C21.8978 2.89782 22.1213 3.43739 22.1213 4C22.1213 4.56261 21.8978 5.10218 21.5 5.5L12 15L8 11L18.5 2.5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>

          {/* Календарь дней недели */}
          <div className="flex gap-2 overflow-x-auto">
            {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((day, index) => (
              <div key={day} className="flex-shrink-0 text-center">
                <div className="text-xs text-gray-500 mb-1">{day}</div>
                <div className={`calendar-day ${index === 2 ? 'selected' : ''}`}>
                  {20 + index}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Сводка */}
        <div className="grid grid-cols-2 gap-4">
          <div className="card text-center">
            <div className="text-3xl font-bold text-green-500 mb-1">{completedPercentage}%</div>
            <div className="text-sm text-gray-500">Выполнено</div>
          </div>
          <div className="card text-center">
            <div className="text-3xl font-bold text-red-500 mb-1">5</div>
            <div className="text-sm text-gray-500">Серия дней</div>
          </div>
        </div>

        {/* Привычки */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Привычки</h2>
          <div className="space-y-3">
            <div className="habit-item">
              <div className="text-2xl">🏃</div>
              <div className="flex-1">
                <div className="font-medium">Спорт</div>
                <div className="text-sm text-orange-500">Нет стрика</div>
              </div>
              <div className="streak-dots">
                {[...Array(7)].map((_, i) => (
                  <div key={i} className="streak-dot inactive" />
                ))}
              </div>
            </div>

            <div className="habit-item">
              <div className="text-2xl">📚</div>
              <div className="flex-1">
                <div className="font-medium">Учёба</div>
                <div className="text-sm text-orange-500">1 день</div>
              </div>
              <div className="streak-dots">
                {[...Array(7)].map((_, i) => (
                  <div key={i} className={`streak-dot ${i === 6 ? 'active' : 'inactive'}`} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Компонент для страницы журнала
function JournalPage() {
  const initData = useInitData()
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newNote, setNewNote] = useState('')
  const [selectedMood, setSelectedMood] = useState('😊')

  // Доступные эмоджи настроения (5 вариантов по спецификации)
  const moodOptions = [
    { emoji: '😡', label: 'Агрессивное' },
    { emoji: '😞', label: 'Плохое' },
    { emoji: '😐', label: 'Нормальное' },
    { emoji: '🙂', label: 'Хорошее' },
    { emoji: '🤩', label: 'Отличное' }
  ]

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

  const loadNotes = async (date) => {
    setLoading(true)
    try {
      const dateStr = format(date, 'yyyy-MM-dd')
      const data = await api(`/notes?date=${dateStr}`)
      setNotes(data)
    } finally {
      setLoading(false)
    }
  }

  const createNote = async () => {
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
    } catch (err) {
      console.error(err)
      alert('Не удалось добавить заметку')
    }
  }

  const cancelCreate = () => {
    setNewNote('')
    setShowCreateForm(false)
  }

  useEffect(() => {
    loadNotes(selectedDate)
    setShowCreateForm(false) // Сбрасываем форму при смене даты
  }, [selectedDate])

  const calendarDays = useMemo(() => {
    const start = startOfMonth(selectedDate)
    const end = endOfMonth(selectedDate)
    const days = eachDayOfInterval({ start, end })

    // Добавляем пустые дни в начале месяца
    const firstDay = getDay(start) === 0 ? 6 : getDay(start) - 1
    const emptyDays = Array(firstDay).fill(null)

    return [...emptyDays, ...days]
  }, [selectedDate])

  const goToPreviousMonth = () => {
    setSelectedDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))
  }

  const goToNextMonth = () => {
    setSelectedDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))
  }

  return (
    <div className="min-h-screen bg-gray-50">
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
              {format(selectedDate, 'MMMM yyyy', { locale: ru })}
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
                {day && (
                  <button
                    className={`calendar-day ${isToday(day) ? 'today' : ''}`}
                    onClick={() => setSelectedDate(day)}
                  >
                    {format(day, 'd')}
                  </button>
                )}
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
                    <div key={note.id} className="bg-gray-50 rounded-xl p-3">
                      <div className="flex items-start gap-3">
                        <span className="text-lg">{note.mood || '😊'}</span>
                        <div className="flex-1">
                          <div className="text-sm text-gray-500 mb-1">
                            {format(new Date(note.created_at), 'HH:mm')}
                          </div>
                          <div className="text-sm">{note.content}</div>
                        </div>
                        <button className="text-gray-400 hover:text-gray-600">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                            <path d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13M18.5 2.5C18.8978 2.10218 19.4374 1.87868 20 1.87868C20.5626 1.87868 21.1022 2.10218 21.5 2.5C21.8978 2.89782 22.1213 3.43739 22.1213 4C22.1213 4.56261 21.8978 5.10218 21.5 5.5L12 15L8 11L18.5 2.5Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : showCreateForm ? (
                /* Форма создания заметки */
                <div className="space-y-4">
                  {/* Выбор настроения */}
                  <div className="flex items-center gap-3">
                    <select
                      value={selectedMood}
                      onChange={(e) => setSelectedMood(e.target.value)}
                      className="bg-gray-100 rounded-lg px-3 py-2 text-sm border-none outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {moodOptions.map((mood) => (
                        <option key={mood.emoji} value={mood.emoji}>
                          {mood.emoji} {mood.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Поле ввода заметки */}
                  <textarea
                    value={newNote}
                    onChange={e => setNewNote(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                    placeholder="Напишите заметку..."
                    rows={4}
                  />

                  {/* Кнопки */}
                  <div className="flex gap-3">
                    <button
                      onClick={createNote}
                      className="btn flex-1 flex items-center justify-center gap-2"
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
                /* Состояние "нет записей" */
                <div className="text-center py-8">
                  <div className="text-6xl mb-4">📖</div>
                  <div className="text-lg font-medium text-gray-700 mb-2">Нет записей</div>
                  <div className="text-sm text-gray-500 mb-6">На эту дату нет записей</div>
                  <button
                    onClick={() => setShowCreateForm(true)}
                    className="btn"
                  >
                    Создать запись
                  </button>
                </div>
              )}
            </>
          )}
        </div>
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
  const [route, setRoute] = useState('tasks')
  const [showCreateTask, setShowCreateTask] = useState(false)

  useEffect(() => {
    tg?.ready()
    tg?.expand()
  }, [])

  const handleCreateTask = () => {
    setShowCreateTask(true)
  }

  const handleTaskCreated = () => {
    setShowCreateTask(false)
    setRoute('tasks')
  }

  const handleBack = () => {
    setShowCreateTask(false)
  }

  if (showCreateTask) {
    return <CreateTaskPage onBack={handleBack} onTaskCreated={handleTaskCreated} />
  }

  return (
    <div>
      {route === 'tasks' ? (
        <TasksPage onCreateTask={handleCreateTask} />
      ) : route === 'statistics' ? (
        <StatisticsPage />
      ) : (
        <JournalPage />
      )}
      <BottomNavigation active={route} onNavigate={setRoute} />
    </div>
  )
}