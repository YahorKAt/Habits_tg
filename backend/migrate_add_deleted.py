"""
Миграция для добавления полей deleted и deleted_at в таблицу tasks
"""
import sqlite3
import os

def migrate():
    # Путь к базе данных
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(backend_dir, "habits.db")
    
    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена. Создайте её сначала через init_db.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, существует ли уже поле deleted
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'deleted' in columns and 'deleted_at' in columns:
            print("Поля 'deleted' и 'deleted_at' уже существуют в таблице tasks. Миграция не требуется.")
            conn.close()
            return
        
        # Добавляем поле deleted
        if 'deleted' not in columns:
            print("Добавление поля 'deleted' в таблицу tasks...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0")
        
        # Добавляем поле deleted_at
        if 'deleted_at' not in columns:
            print("Добавление поля 'deleted_at' в таблицу tasks...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN deleted_at DATETIME")
        
        conn.commit()
        print("✅ Миграция успешно выполнена. Поля 'deleted' и 'deleted_at' добавлены в таблицу tasks.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка при выполнении миграции: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

