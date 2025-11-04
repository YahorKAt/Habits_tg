"""
Миграция для добавления поля streak в таблицу tasks
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
        # Проверяем, существует ли уже поле streak
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'streak' in columns:
            print("Поле 'streak' уже существует в таблице tasks. Миграция не требуется.")
            conn.close()
            return
        
        # Добавляем поле streak
        print("Добавление поля 'streak' в таблицу tasks...")
        cursor.execute("ALTER TABLE tasks ADD COLUMN streak INTEGER NOT NULL DEFAULT 0")
        
        conn.commit()
        print("✅ Миграция успешно выполнена. Поле 'streak' добавлено в таблицу tasks.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка при выполнении миграции: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

