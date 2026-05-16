# Task Manager - Инструкция по запуску

## Требования

- **Docker** и **Docker Compose**

---

## Установка

**Вариант 1: Git clone (рекомендуется)**
```bash
git clone https://github.com/DanyaMr/taskmanager.git
cd taskmanager
```

**Вариант 2: Скачать ZIP**
- Нажми зелёную кнопку "Code" на GitHub
- "Download ZIP"
- Распакуй архив (папка будет называться `taskmanager-main`)

---

## Быстрый запуск через Docker

### 1. Установка Docker

**macOS:**
```bash
# Установка через Homebrew
brew install --cask docker

# Или скачать с docker.com
```

**Windows:**
```bash
# Скачать и установить с docker.com
https://www.docker.com/products/docker-desktop/
```

### 2. Запуск сервера

**Для Mac и систем без NVIDIA GPU:**
```bash
# Сборка и запуск (CPU-версия)
docker-compose up --build

# Или в фоновом режиме
docker-compose up -d --build
```

**Для систем с NVIDIA GPU:**
```bash
# Использовать Dockerfile.gpu
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

### 3. Открыть веб-интерфейс

```
http://localhost:8000/tasks
http://localhost:8000/employees
```

### 4. Остановка сервера

```bash
# Остановка
docker-compose down

# Остановка с удалением томов (база данных удалится!)
docker-compose down -v
```

---

## Запуск без Docker (не рекомендуется)

### Требования
- Python 3.10+
- pip

### macOS / Linux

```bash
cd taskmanager
python3 -m venv venv
source venv/bin/activate
pip install -r department/requirements.txt

# Запуск через модуль (важно для работы импортов!)
python -m uvicorn department.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Windows

```cmd
cd taskmanager
py -m venv venv
venv\Scripts\activate
pip install -r department\requirements.txt

# Запуск через модуль (важно для работы импортов!)
py -m uvicorn department.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Настройка LLM (опционально)

Для использования LLM-функций (декомпозиция задач, прогнозирование):

1. Установите [LM Studio](https://lmstudio.ai/)
2. Скачайте модель (например, Qwen2.5-7B-Instruct)
3. Запустите локальный сервер в LM Studio:
   - Порт: `1234`
   - Модель: выбранная модель

Сервис автоматически подключится к `http://localhost:1234/v1`

---

## Примечания

- База данных хранится в `department/database/department.db`
- Векторное хранилище RAG находится в `department/rag/vector_db/chroma.sqlite3`
- Эти файлы сохраняются между запусками благодаря volumes в docker-compose.yml

## Сброс базы данных

**Через Docker:**
```bash
docker-compose exec taskmanager python department/database/reset_database.py
```

**Без Docker:**
```bash
python -m department.database.reset_database
```
