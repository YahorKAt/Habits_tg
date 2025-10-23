#!/usr/bin/env python3
"""
Скрипт для миграции базы данных - добавление поля mood в таблицу notes
"""

import sqlite3
import os

def migrate_notes_mood():
    db_path = "backend/habits.db"
    
    if not os.path.exists(db_path):
        print("❌ База данных не найдена")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, есть ли уже поле mood
        cursor.execute("PRAGMA table_info(notes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'mood' not in columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN mood VARCHAR(10)")
            print("✅ Добавлено поле 'mood' в таблицу notes")
        else:
            print("✅ Поле 'mood' уже существует")
        
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
    print("🔍 Миграция поля mood для заметок...")
    migrate_notes_mood()

