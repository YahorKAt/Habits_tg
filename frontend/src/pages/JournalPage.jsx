/**
 * Страница журнала
 * Отображает календарь с заметками и настроением
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { format, isToday, startOfMonth, endOfMonth, eachDayOfInterval, getDay } from 'date-fns'
import { ru } from 'date-fns/locale'
import { createApiClient } from '../utils/api.js'
import { useInitData } from '../hooks/useTelegram.js'
import { MOOD_OPTIONS } from '../constants/index.js'
import { formatDateForAPI } from '../utils/dateUtils.js'
import MoodIcon from '../components/MoodIcon.jsx'
import * as noteService from '../services/noteService.js'

/**
 * Нормализует значение настроения
 */
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

/**
 * Преобразует настроение в CSS классы
 */
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

/**
 * Страница журнала
 */
export default function JournalPage() {
  const initData = useInitData()
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newNote, setNewNote] = useState('')
  const [selectedMood, setSelectedMood] = useState('')
  const [monthMoodMap, setMonthMoodMap] = useState({})
  const [editingNote, setEditingNote] = useState(null)
  const [editContent, setEditContent] = useState('')
  const [editMood, setEditMood] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const api = useMemo(() => createApiClient(initData), [initData])

  const loadNotes = useCallback(async (date, showLoading = true) => {
    console.log(`📋 [JournalPage] Загрузка заметок для даты:`, date)
    if (showLoading) {
      setLoading(true)
    }
    try {
      const data = await noteService.getNotesByDate(api, date)
      setNotes(data)
      console.log(`✅ [JournalPage] Загружено ${data.length} заметок`)
    } catch (error) {
      console.error(`❌ [JournalPage] Ошибка загрузки заметок:`, error)
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }, [api])

  const loadMonthMood = useCallback(async (date) => {
    const year = date.getFullYear()
    const month = date.getMonth() + 1

    try {
      const data = await noteService.getNotesByMonth(api, year, month)
      const map = {}
      if (Array.isArray(data)) {
        const notesByDate = {}
        data.forEach(note => {
          if (note.date && !notesByDate[note.date]) {
            notesByDate[note.date] = note
          }
        })

        Object.entries(notesByDate).forEach(([dateStr, note]) => {
          if (note?.mood) {
            map[dateStr] = moodToClasses(note.mood)
          }
        })
      }
      setMonthMoodMap(map)
    } catch (e) {
      console.error('Error loading month mood:', e)
    }
  }, [api])

  const createNote = async () => {
    if (isCreating) return
    if (!selectedMood) {
      alert('Пожалуйста, выберите настроение')
      return
    }
    setIsCreating(true)
    try {
      const created = await noteService.createNote(api, {
        content: newNote.trim(),
        date: format(selectedDate, 'yyyy-MM-dd'),
        mood: selectedMood
      })
      const updatedNotes = [created, ...notes]
      setNotes(updatedNotes)
      setNewNote('')
      setShowCreateForm(false)
      const dateStrForMap = formatDateForAPI(selectedDate)
      const updatedMap = { ...monthMoodMap, [dateStrForMap]: moodToClasses(selectedMood) }
      setMonthMoodMap(updatedMap)
    } catch (err) {
      console.error(err)
      alert('Не удалось добавить заметку')
    } finally {
      setIsCreating(false)
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
    if (isSaving) return
    if (!editingNote) return
    if (!editMood) {
      alert('Пожалуйста, выберите настроение')
      return
    }
    setIsSaving(true)
    const payload = {
      content: editContent.trim(),
      date: format(selectedDate, 'yyyy-MM-dd'),
      mood: editMood,
    }
    try {
      try {
        const updated = await noteService.updateNote(api, editingNote.id, payload)
        setNotes(notes.map(n => n.id === editingNote.id ? updated : n))
      } catch (e) {
        await noteService.deleteNote(api, editingNote.id)
        const created = await noteService.createNote(api, payload)
        setNotes([created, ...notes.filter(n => n.id !== editingNote.id)])
      }

      const dateStrForMap = formatDateForAPI(selectedDate)
      const updatedMap = { ...monthMoodMap, [dateStrForMap]: moodToClasses(editMood) }
      setMonthMoodMap(updatedMap)

      cancelEdit()
    } catch (err) {
      console.error(err)
      alert('Не удалось сохранить изменения')
    } finally {
      setIsSaving(false)
    }
  }

  useEffect(() => {
    loadNotes(selectedDate, true)
    setShowCreateForm(false)
  }, [selectedDate, loadNotes])

  useEffect(() => {
    loadMonthMood(selectedDate)
  }, [selectedDate.getFullYear(), selectedDate.getMonth(), loadMonthMood])

  const calendarDays = useMemo(() => {
    const start = startOfMonth(selectedDate)
    const end = endOfMonth(selectedDate)
    const days = eachDayOfInterval({ start, end })

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
      <div className="bg-white px-4 py-4">
        <h1 className="text-xl font-semibold">Журнал</h1>
      </div>

      <div className="p-4 pb-24 space-y-6">
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

          <div className="grid grid-cols-7 gap-1 mb-2">
            {['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'].map(day => (
              <div key={day} className="text-center text-xs text-gray-500 py-2">
                {day}
              </div>
            ))}
          </div>

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

        <div className="card">
          <h3 className="text-lg font-semibold mb-4">
            {format(selectedDate, 'd MMMM yyyy г.', { locale: ru })}
          </h3>

          {loading && <div className="text-center text-gray-500">Загрузка...</div>}

          {!loading && (
            <>
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
                            <button onClick={saveEdit} disabled={!editMood || isSaving} className="btn flex-1 disabled:opacity-50">
                              {isSaving ? 'Сохранение...' : 'Сохранить'}
                            </button>
                            <button onClick={cancelEdit} className="btn-secondary flex-1">
                              Отмена
                            </button>
                          </div>
                        </div>
                      </div>
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
                  ))}
                </div>
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
                      disabled={!selectedMood || isCreating}
                      className="btn flex-1 flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <path d="M19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H16L21 8V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      {isCreating ? 'Сохранение...' : 'Сохранить'}
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
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

