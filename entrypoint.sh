#!/bin/bash

# Настройка PYTHONPATH
export PYTHONPATH=/app

# Инициализация базы данных (добавление начальных навыков)
echo "🔧 Initializing database..."
python department/database/setup.py

# Запуск сервера
echo "🚀 Starting server..."
exec uvicorn department.api.main:app --host 0.0.0.0 --port 8000
