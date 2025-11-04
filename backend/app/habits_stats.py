from typing import List, Dict, Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from . import models

def get_habits_stats(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Получает статистику по привычкам (группам) для пользователя.
    Для каждой группы возвращает максимальный стрик среди всех задач этой группы.
    """
    # Получаем все задачи пользователя (не удаленные)
    stmt = select(models.Task).where(
        models.Task.user_id == user_id,
        models.Task.deleted == False
    )
    tasks = db.execute(stmt).scalars().all()
    
    # Группируем задачи по категориям и находим максимальный стрик для каждой группы
    category_stats = {}
    
    for task in tasks:
        category = task.category or 'general'
        
        if category not in category_stats:
            category_stats[category] = {
                'category': category,
                'max_streak': 0,
                'has_tasks': True
            }
        
        # Обновляем максимальный стрик для группы
        if task.streak > category_stats[category]['max_streak']:
            category_stats[category]['max_streak'] = task.streak
    
    # Преобразуем в список
    result = list(category_stats.values())
    
    # Сортируем по максимальному стрику (по убыванию)
    result.sort(key=lambda x: x['max_streak'], reverse=True)
    
    return result

