// Локальный JavaScript без внешних зависимостей
document.addEventListener('DOMContentLoaded', function() {
    // Обновляем метрики с API
    fetch('/api/v1/dashboard')
        .then(res => res.json())
        .then(data => {
        document.getElementById('automation-rate').textContent =
        data.automation_rate.toFixed(1) + '%';
        document.getElementById('forecast-accuracy').textContent =
        (data.forecast_accuracy * 100).toFixed(0) + '%';
    })
        .catch(err => console.error('Ошибка загрузки метрик:', err));
});