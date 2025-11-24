/**
 * Страница статистики
 * Отображает статистику выполнения задач и привычки
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import { createApiClient } from '../utils/api.js'
import { useInitData } from '../hooks/useTelegram.js'
import { TASK_CATEGORIES } from '../constants/index.js'
import * as statisticsService from '../services/statisticsService.js'

/**
 * Страница статистики
 */
export default function StatisticsPage() {
  const initData = useInitData()
  const [period, setPeriod] = useState('day')
  const [stats, setStats] = useState(null)
  const [habitsStats, setHabitsStats] = useState([])
  const [loading, setLoading] = useState(false)

  const api = useMemo(() => createApiClient(initData), [initData])

  const loadStats = useCallback(async (p) => {
    console.log(`📊 [StatisticsPage] Загрузка статистики за период: ${p}`)
    setLoading(true)
    try {
      const data = await statisticsService.getStatistics(api, p)
      setStats(data)
      console.log(`✅ [StatisticsPage] Статистика загружена:`, data)
    } catch (error) {
      console.error(`❌ [StatisticsPage] Ошибка загрузки статистики:`, error)
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
    console.log(`📊 [StatisticsPage] Загрузка статистики по привычкам`)
    try {
      const data = await statisticsService.getHabitsStatistics(api)
      setHabitsStats(data)
      console.log(`✅ [StatisticsPage] Статистика по привычкам загружена: ${data.length} привычек`)
    } catch (error) {
      console.error(`❌ [StatisticsPage] Ошибка загрузки статистики по привычкам:`, error)
      setHabitsStats([])
    }
  }, [api])

  useEffect(() => {
    loadStats(period)
  }, [period, loadStats])

  useEffect(() => {
    loadHabitsStats()
  }, [loadHabitsStats])

  const handlePeriodChange = useCallback((e) => {
    setPeriod(e.target.value)
  }, [])

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

  const completionPercentage = useMemo(() => {
    if (!stats || stats.total === 0) return 0
    return Math.round(((stats.completed || 0) / stats.total) * 100)
  }, [stats])

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className="bg-white px-4 py-4">
        <h1 className="text-xl font-semibold">Статистика</h1>
      </div>

      <div className="p-4 pb-24 space-y-6">
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

