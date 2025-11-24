/**
 * Компонент нижней навигации
 */

export default function BottomNavigation({ active, onNavigate }) {
  const navItems = [
    {
      id: 'tasks',
      label: 'Задачи',
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    },
    {
      id: 'statistics',
      label: 'Статистика',
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M3 3V21H21M7 16L12 11L16 15L21 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    },
    {
      id: 'journal',
      label: 'Журнал',
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M4 19.5C4 18.1193 5.11929 17 6.5 17H20M4 19.5C4 20.8807 5.11929 22 6.5 22H20M4 19.5V5C4 3.89543 4.89543 3 6 3H18C19.1046 3 20 3.89543 20 5V19.5M8 7H16M8 11H12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    }
  ]

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100">
      <div className="flex justify-around py-2">
        {navItems.map(item => (
          <button
            key={item.id}
            className={`nav-item ${active === item.id ? 'active' : 'inactive'}`}
            onClick={() => onNavigate(item.id)}
          >
            {item.icon}
            <span className="text-xs font-medium">{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

