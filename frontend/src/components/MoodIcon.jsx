/**
 * Компонент для отображения иконки настроения
 */

const MOOD_CONFIG = {
  very_bad: { fill: '#EF4444', stroke: '#B91C1C', mouth: 'down' },
  bad: { fill: '#FCA5A5', stroke: '#EF4444', mouth: 'down' },
  neutral: { fill: '#FDE047', stroke: '#CA8A04', mouth: 'flat' },
  good: { fill: '#86EFAC', stroke: '#16A34A', mouth: 'up' },
  very_good: { fill: '#22C55E', stroke: '#15803D', mouth: 'up' },
}

/**
 * Компонент иконки настроения
 * @param {string} value - значение настроения
 * @param {number} size - размер иконки в пикселях
 */
export default function MoodIcon({ value, size = 20 }) {
  const config = MOOD_CONFIG[value] || MOOD_CONFIG.neutral

  const renderMouth = () => {
    switch (config.mouth) {
      case 'up':
        return <path d="M16 30 C 20 36, 28 36, 32 30" stroke="#1F2937" strokeWidth="3" fill="none" strokeLinecap="round" />
      case 'down':
        return <path d="M16 34 C 20 28, 28 28, 32 34" stroke="#1F2937" strokeWidth="3" fill="none" strokeLinecap="round" />
      case 'flat':
        return <path d="M16 32 L 32 32" stroke="#1F2937" strokeWidth="3" strokeLinecap="round" />
      default:
        return null
    }
  }

  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <circle cx="24" cy="24" r="22" fill={config.fill} stroke={config.stroke} strokeWidth="2" />
      <circle cx="17" cy="20" r="3" fill="#1F2937" />
      <circle cx="31" cy="20" r="3" fill="#1F2937" />
      {renderMouth()}
    </svg>
  )
}

