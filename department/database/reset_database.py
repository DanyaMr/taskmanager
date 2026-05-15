"""
Полное пересоздание базы данных с исправленной схемой
"""

import os
from pathlib import Path
from enterprise_twin.models.department.database.db_models import  Base
from enterprise_twin.models.department.database.service import DatabaseService

def reset_database():
    # Определяем путь к БД
    BASE_DIR = Path(__file__).resolve().parent
    DB_PATH = BASE_DIR / "department.db"

    # Удаляем старую БД если существует
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print(f"🗑️ Старая БД удалена: {DB_PATH}")

    # Создаем новую БД
    db = DatabaseService()
    db.init_database()
    print("✅ Новая БД создана с исправленной схемой")

if __name__ == "__main__":
    reset_database()