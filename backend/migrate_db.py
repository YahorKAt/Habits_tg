#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database migration script
"""

import sqlite3
import os
import sys

def migrate_db():
    # Determine the correct path to the database
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "habits.db")
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at path: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Migration for notes - add mood field
        cursor.execute("PRAGMA table_info(notes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'mood' not in columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN mood VARCHAR(10)")
            print("[OK] Added 'mood' field to notes table")
        else:
            print("[OK] Field 'mood' already exists in notes")
        
        # Migration for tasks - add frequency and description fields
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'frequency' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN frequency VARCHAR(20) DEFAULT 'daily'")
            print("[OK] Added 'frequency' field to tasks table")
        else:
            print("[OK] Field 'frequency' already exists in tasks")
        
        if 'description' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN description VARCHAR(1000)")
            print("[OK] Added 'description' field to tasks table")
        else:
            print("[OK] Field 'description' already exists in tasks")
        
        conn.commit()
        print("[OK] Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("Database migration...")
    success = migrate_db()
    if success:
        print("\n[OK] Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n[ERROR] Migration failed with errors")
        sys.exit(1)

