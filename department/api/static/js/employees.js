console.log('=== EMPLOYEES.JS LOADED ==='); // <-- ДОБАВЬТЕ ЭТО
// Полифил для axios-like API
window.axios = {
    get: async (url) => {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return { data: await response.json() };
    },

    post: async (url, data) => {
        const response = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw { response: { data: errorData } };
        }
        return { data: await response.json() };
    },

    delete: async (url) => {
        const response = await fetch(url, { method: 'DELETE' });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw { response: { data: errorData } };
        }
        // Обработка 204 No Content - пустой ответ
        if (response.status === 204) {
            return { data: null };
        }
        const text = await response.text();
        if (!text || text.trim() === '') {
            return { data: null };
        }
        try {
            return { data: JSON.parse(text) };
        } catch (e) {
            return { data: null };
        }
    }
};


// ВЫЗОВ ПРИ ЗАГРУЗКЕ
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM загружен, вызываю loadEmployees()'); // <-- ДОБАВЬТЕ
    loadEmployees();
});

function toggleTasks(empId) {
    const div = document.getElementById(`tasks-${empId}`);
    div.style.display = div.style.display === 'none' ? 'block' : 'none';
}

// Создание сотрудника
document.getElementById('create-employee-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Добавляем префикс "skill_" к навыкам для соответствия с задачами
    const skills = document.getElementById('emp_skills').value.split(',').map(s => s.trim()).filter(s => s);
    const skillIds = skills.map(s => {
        // Если навык уже начинается с "skill_", не добавляем префикс
        if (s.startsWith('skill_')) return s;
        return `skill_${s}`;
    });

    const empData = {
        id: document.getElementById('emp_id').value,
        name: document.getElementById('emp_name').value,
        type: document.getElementById('emp_type').value,
        max_capacity: parseFloat(document.getElementById('emp_capacity').value),
        skill_ids: skillIds,
        config: {}
    };

    try {
        const response = await fetch('/api/v1/employees/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(empData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка создания');
        }

        document.getElementById('create-emp-result').innerHTML = '<span style="color: green;">Сотрудник создан!</span>';
        loadEmployees();
    } catch (error) {
        document.getElementById('create-emp-result').innerHTML = `<span style="color: red;">Ошибка: ${error.message}</span>`;
    }
});

// Удаление сотрудника
async function deleteEmployee(empId) {
    if (!confirm(`Удалить сотрудника ${empId}?`)) return;

    // Находим строку по data-атрибуту
    const row = document.querySelector(`tr[data-employee-id="${empId}"]`);
    
    if (row) {
        row.style.opacity = '0.5';
        row.style.transition = 'opacity 0.3s';
    }

    try {
        await axios.delete(`/api/employees/${empId}`);
        
        // Удаляем строку из DOM
        if (row) {
            row.remove();
        }
        console.log(`✅ Сотрудник ${empId} удален`);
    } catch (error) {
        console.error('❌ Ошибка удаления:', error);
        alert(`Ошибка: ${error.response?.data?.detail || error.message || 'Неизвестная ошибка'}`);
        // Восстанавливаем строку если ошибка
        if (row) {
            row.style.opacity = '1';
        }
    }
}
async function loadEmployees() {
    console.log('Загрузка сотрудников...'); // <-- ДОБАВЬТЕ
    try {
        const response = await axios.get('/api/v1/employees/detailed');
        console.log('Получены данные:', response.data); // <-- ДОБАВЬТЕ
        const employees = response.data;
        const tbody = document.getElementById('employees-table');

        if (!employees || employees.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 20px;">Нет данных о сотрудниках</td></tr>';
            return;
        }

        tbody.innerHTML = employees.map(emp => `
            <tr class="${emp.type}" data-employee-id="${emp.id}">
                <td>${emp.id}</td>
                <td><strong>${emp.name}</strong></td>
                <td>${emp.type === 'digital' ? '🤖 Цифровой' : '👤 Человек'}</td>
                <td>
                    <div style="background: #eee; height: 20px; position: relative;">
                        <div style="background: ${emp.current_load > 0.8 ? 'red' : emp.current_load > 0.5 ? 'orange' : 'green'};
                                     height: 100%; width: ${emp.current_load * 100}%"></div>
                        <span style="position: absolute; left: 5px; top: 2px;">
                            ${(emp.current_load * 100).toFixed(1)}%
                        </span>
                    </div>
                </td>
                <td>${emp.max_capacity} ч/нед</td>
                <td>${emp.skills.map(s => `<span class="skill-tag">${s.name}</span>`).join('')}</td>
                <td>
                    <div class="collapse-btn" onclick="toggleTasks('${emp.id}')">${emp.task_count} задач ▼</div>
                    <div id="tasks-${emp.id}" style="display:none; margin-top: 10px;">
                        ${emp.tasks.map(t => `<div style="font-size: 12px; margin: 2px 0;">${t.title} (${t.status})</div>`).join('')}
                    </div>
                </td>
                <td>
                    <button onclick="deleteEmployee('${emp.id}')" class="delete-btn"
                            ${emp.task_count > 0 ? 'disabled' : ''}>Удалить</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('ОШИБКА ЗАГРУЗКИ:', error); // <-- ДОБАВЬТЕ
        document.getElementById('employees-table').innerHTML =
        `<tr><td colspan="8" style="text-align: center; color: red; padding: 20px;">
            Ошибка: ${error.message}
        </td></tr>`;
    }
}
// Вызов при загрузке

document.addEventListener('DOMContentLoaded', loadEmployees);