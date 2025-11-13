/**
 * Хуки для работы с Telegram WebApp API
 */

/**
 * Хук для получения Telegram WebApp объекта
 */
export function useTelegram() {
  const tg = window.Telegram?.WebApp
  if (tg?.initData) {
    console.log("Telegram initData found")
  } else {
    console.log("No Telegram data detected")
  }
  return tg
}

/**
 * Хук для получения initData из Telegram
 */
export function useInitData() {
  const tg = useTelegram()
  const initData = tg?.initData || ''

  // Диагностика для отладки
  if (!initData) {
    console.warn('⚠️ initData is empty!', {
      tg: !!tg,
      hasInitData: !!tg?.initData,
      initDataUnsafe: tg?.initDataUnsafe
    })
  } else {
    console.log('✅ initData available, length:', initData.length)
  }

  return initData
}

