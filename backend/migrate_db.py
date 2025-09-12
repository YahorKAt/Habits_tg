#!/usr/bin/env python3
"""
Скрипт миграции для добавления полей повторяющихся задач
"""
import sqlite3
import os
from datetime import datetime

def migrate_database():
    db_path = "habits.db"
    
    if not os.path.exists(db_path):
        print("База данных не найдена. Создайте её сначала, запустив приложение.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, есть ли уже новые поля
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'repeat_type' not in columns:
            print("Добавляем поле repeat_type...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN repeat_type TEXT DEFAULT 'NONE'")
            
        if 'repeat_interval' not in columns:
            print("Добавляем поле repeat_interval...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN repeat_interval INTEGER DEFAULT 1")
            
        if 'next_due_date' not in columns:
            print("Добавляем поле next_due_date...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN next_due_date DATETIME")
            
        if 'end_date' not in columns:
            print("Добавляем поле end_date...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN end_date DATETIME")
            
        if 'last_completed_date' not in columns:
            print("Добавляем поле last_completed_date...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN last_completed_date DATETIME")
        
        # Добавляем поле для группы задачи
        if 'category' not in columns:
            print("Добавляем поле category...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT 'general'")
        
        # Обновляем существующие записи
        cursor.execute("UPDATE tasks SET repeat_type = 'NONE' WHERE repeat_type IS NULL")
        cursor.execute("UPDATE tasks SET repeat_interval = 1 WHERE repeat_interval IS NULL")
        cursor.execute("UPDATE tasks SET category = 'general' WHERE category IS NULL")
        
        # Мигрируем старые значения enum на новые
        print("Мигрируем значения enum...")
        cursor.execute("UPDATE tasks SET repeat_type = 'NONE' WHERE repeat_type = 'none'")
        cursor.execute("UPDATE tasks SET repeat_type = 'DAILY' WHERE repeat_type = 'daily'")
        cursor.execute("UPDATE tasks SET repeat_type = 'WEEKLY' WHERE repeat_type = 'weekly'")
        cursor.execute("UPDATE tasks SET repeat_type = 'MONTHLY' WHERE repeat_type = 'monthly'")
        cursor.execute("UPDATE tasks SET repeat_type = 'CUSTOM' WHERE repeat_type = 'custom'")
        
        conn.commit()
        print("Миграция завершена успешно!")
        
        # Создаем таблицу заметок, если её нет
        print("Создаем таблицу заметок...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем индекс для быстрого поиска заметок по пользователю и дате
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_user_date ON notes(user_id, date)")
        
        conn.commit()
        print("Таблица заметок создана успешно!")
        
        # Показываем структуру таблицы
        cursor.execute("PRAGMA table_info(tasks)")
        print("\nСтруктура таблицы tasks:")
        for column in cursor.fetchall():
            print(f"  {column[1]} ({column[2]}) - {column[4]}")
            
        # Показываем текущие значения enum
        cursor.execute("SELECT DISTINCT repeat_type FROM tasks")
        print("\nТекущие значения repeat_type:")
        for row in cursor.fetchall():
            print(f"  {row[0]}")
            
    except Exception as e:
        print(f"Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Запуск миграции базы данных...")
    migrate_database()
