#!/usr/bin/env python3
"""
Скрипт для миграции базы данных SQLite
Добавляет необходимые поля в таблицы notes и tasks
"""

import sqlite3
import os
import sys


def migrate_db():
    db_path = "backend/habits.db"
    # Determine the correct path to the database
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "habits.db")

    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Миграция для notes - добавить поле mood
        cursor.execute("PRAGMA table_info(notes)")
        notes_columns = [column[1] for column in cursor.fetchall()]

        if 'mood' not in notes_columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN mood VARCHAR(10)")
            print("✅ Добавлено поле 'mood' в таблицу notes")
        else:
            print("✅ Поле 'mood' уже существует в notes")

        # Получаем колонки таблицы tasks один раз
        cursor.execute("PRAGMA table_info(tasks)")
        tasks_columns = [row[1] for row in cursor.fetchall()]

        # Миграция для tasks - добавить поле frequency
        if 'frequency' not in tasks_columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN frequency VARCHAR(20) DEFAULT 'daily'")
            print("✅ Добавлено поле 'frequency' в таблицу tasks")
        else:
            print("✅ Поле 'frequency' уже существует в tasks")
        
        # Миграция для tasks - добавить поле description
        if 'description' not in tasks_columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN description VARCHAR(1000)")
            print("✅ Добавлено поле 'description' в таблицу tasks")
        else:
            print("✅ Поле 'description' уже существует в tasks")

        # Миграция для tasks - добавить поле streak
        if 'streak' not in tasks_columns:
            print("Добавление поля 'streak' в таблицу tasks...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN streak INTEGER NOT NULL DEFAULT 0")
            print("✅ Поле 'streak' добавлено в таблицу tasks")
        else:
            print("✅ Поле 'streak' уже существует в таблице tasks")

        # Миграция для tasks - добавить поля deleted и deleted_at
        if 'deleted' not in tasks_columns:
            print("Добавление поля 'deleted' в таблицу tasks...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0")
            print("✅ Поле 'deleted' добавлено в таблицу tasks")
        else:
            print("✅ Поле 'deleted' уже существует в таблице tasks")

        if 'deleted_at' not in tasks_columns:
            print("Добавление поля 'deleted_at' в таблицу tasks...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN deleted_at DATETIME")
            print("✅ Поле 'deleted_at' добавлено в таблицу tasks")
        else:
            print("✅ Поле 'deleted_at' уже существует в таблице tasks")

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
    success = migrate_db()
    if success:
        print("\n[OK] Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n[ERROR] Migration failed with errors")
        sys.exit(1)