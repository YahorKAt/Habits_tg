import React, { useEffect, useMemo, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function useTelegram() {
  const tg = window.Telegram?.WebApp
  return tg
}

function useInitData() {
  const tg = useTelegram()
  const initData = tg?.initData || ''
  return initData
}

function Header({ onNavigate, active }) {
  return (
    <div className="sticky top-0 z-10 backdrop-blur bg-white/70 dark:bg-gray-900/70">
      <div className="max-w-xl mx-auto px-4 py-3 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Habits</h1>
        <div className="flex gap-2">
          <button className={`btn !px-3 !py-1.5 ${active === 'tasks' ? '!bg-blue-700' : ''}`} onClick={() => onNavigate('tasks')}>Tasks</button>
          <button className={`btn !px-3 !py-1.5 ${active === 'stats' ? '!bg-blue-700' : ''}`} onClick={() => onNavigate('stats')}>Stats</button>
        </div>
      </div>
    </div>
  )
}

function TaskItem({ task, onToggleTask, onAddSubtask, onToggleSubtask, onDelete }) {
  const [subTitle, setSubTitle] = useState('')
  return (
    <div className="card animate-fadeInUp">
      <div className="flex items-center gap-3">
        <input type="checkbox" checked={task.completed} onChange={() => onToggleTask(task)} />
        <div className={`flex-1 ${task.completed ? 'line-through opacity-60' : ''}`}>{task.title}</div>
        <button onClick={() => onDelete(task)} className="text-red-500 hover:text-red-600">✕</button>
      </div>
      <div className="mt-2 pl-7 space-y-2">
        {task.subtasks?.map(st => (
          <div key={st.id} className="flex items-center gap-3">
            <input type="checkbox" checked={st.completed} onChange={() => onToggleSubtask(task, st)} />
            <div className={`flex-1 ${st.completed ? 'line-through opacity-60' : ''}`}>{st.title}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <input value={subTitle} onChange={e => setSubTitle(e.target.value)} className="input" placeholder="Add subtask" />
        <button className="btn" onClick={() => { if (!subTitle) return; onAddSubtask(task, subTitle); setSubTitle('') }}>Add</button>
      </div>
    </div>
  )
}

function Tasks() {
  const initData = useInitData()
  const [loading, setLoading] = useState(false)
  const [title, setTitle] = useState('')
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

  const addTask = async () => {
    if (!title) return
    const task = await api('/task', { method: 'POST', body: JSON.stringify({ title }) })
    setTitle('')
    setItems(prev => [task, ...prev])
  }

  const deleteTask = async (task) => {
    await api(`/task/${task.id}`, { method: 'DELETE' })
    setItems(prev => prev.filter(t => t.id !== task.id))
  }

  const toggleTask = async (task) => {
    const updated = await api(`/task/${task.id}/complete`, { method: 'POST' })
    setItems(prev => prev.map(t => t.id === task.id ? updated : t))
  }

  const addSubtask = async (task, subTitle) => {
    const st = await api('/subtask', { method: 'POST', body: JSON.stringify({ task_id: task.id, title: subTitle }) })
    setItems(prev => prev.map(t => t.id === task.id ? { ...t, subtasks: [...(t.subtasks || []), st] } : t))
  }

  const toggleSubtask = async (task, st) => {
    const updated = await api(`/subtask/${st.id}/complete`, { method: 'POST' })
    setItems(prev => prev.map(t => t.id === task.id ? { ...t, subtasks: t.subtasks.map(s => s.id === st.id ? updated : s) } : t))
  }

  return (
    <div className="max-w-xl mx-auto p-4 space-y-3">
      <div className="card">
        <div className="flex gap-2">
          <input value={title} onChange={e => setTitle(e.target.value)} className="input" placeholder="New task" />
          <button onClick={addTask} className="btn">Add</button>
        </div>
      </div>
      {loading && <div className="text-center opacity-70">Loading...</div>}
      <div className="space-y-3">
        {items.map(task => (
          <TaskItem key={task.id} task={task} onToggleTask={toggleTask} onAddSubtask={addSubtask} onToggleSubtask={toggleSubtask} onDelete={deleteTask} />
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
    <div className="max-w-xl mx-auto p-4">
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
            <div className="card"><div className="text-sm opacity-70">Total</div><div className="text-2xl font-semibold">{stats.total_completed}</div></div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const tg = useTelegram()
  const [route, setRoute] = useState('tasks')

  useEffect(() => {
    tg?.ready()
    tg?.expand()
    const theme = tg?.colorScheme
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [])

  return (
    <div>
      <Header onNavigate={setRoute} active={route} />
      {route === 'tasks' ? <Tasks /> : <Stats />}
    </div>
  )
}




