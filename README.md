# Task Manager - Инструкция по запуску

## Требования

- **Python 3.10** или выше
- **pip** (менеджер пакетов Python)

---

## Установка и запуск

### macOS

#### 1. Установка Python
```bash
# Проверка версии Python
python3 --version

# Если Python не установлен, установите через Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.10
```

#### 2. Установка зависимостей
```bash
cd taskmanager
python3 -m venv venv
source venv/bin/activate
pip install -r department/requirements.txt
```

#### 3. Запуск сервера
```bash
uvicorn department.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. Открыть веб-интерфейс
```
http://localhost:8000/tasks
http://localhost:8000/employees
```

---

### Windows

#### 1. Установка Python
1. Скачайте Python 3.10+ с [python.org](https://www.python.org/downloads/)
2. При установке отметьте галочку **"Add Python to PATH"**
3. Нажмите "Install Now"

#### 2. Установка зависимостей
```cmd
cd models-2
py -m venv venv
venv\Scripts\activate
pip install -r department\requirements.txt
```

#### 3. Запуск сервера
```cmd
uvicorn department.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. Открыть веб-интерфейс
```
http://localhost:8000/tasks
http://localhost:8000/employees
```

---

## Настройка LLM (опционально)

Для использования LLM-функций (декомпозиция задач, прогнозирование):

1. Установите [LM Studio](https://lmstudio.ai/)
2. Скачайте модель (например, Qwen2.5-7B-Instruct)
3. Запустите локальный сервер в LM Studio:
   - Порт: `1234`
   - Модель: выбранная модель
4. Сервис автоматически подключится к `http://localhost:1234/v1`

---

## Примечания

- База данных создается автоматически при первом запуске
- Векторное хранилище RAG находится в `department/rag/vector_db/chroma.sqlite3`
- Для сброса базы данных выполните:
  ```bash
  python department/database/reset_database.py
  ```
