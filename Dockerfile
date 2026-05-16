FROM python:3.10-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка Python зависимостей
# CPU-версия torch для Mac и систем без NVIDIA GPU
COPY department/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Копирование проекта
COPY . .

# Копирование entrypoint скрипта
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Экспортирование порта
EXPOSE 8000

# Запуск через entrypoint с bash
ENTRYPOINT ["bash", "./entrypoint.sh"]
