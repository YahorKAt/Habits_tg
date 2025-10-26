#!/usr/bin/env python3
"""
Скрипт для миграции базы данных - добавление полей mood в notes и frequency в tasks
"""

import sqlite3
import os

def migrate_db():
    db_path = "backend/habits.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Миграция для notes - добавить поле mood
        cursor.execute("PRAGMA table_info(notes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'mood' not in columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN mood VARCHAR(10)")
            print("✅ Добавлено поле 'mood' в таблицу notes")
        else:
            print("✅ Поле 'mood' уже существует в notes")
        
        # Миграция для tasks - добавить поле frequency
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'frequency' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN frequency VARCHAR(20) DEFAULT 'daily'")
            print("✅ Добавлено поле 'frequency' в таблицу tasks")
        else:
            print("✅ Поле 'frequency' уже существует в tasks")
        
        conn.commit()
        print("🎉 Миграция завершена успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔍 Миграция базы данных...")
    migrate_db()

