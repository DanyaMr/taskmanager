// Полифил для axios-like API
window.axios = {
    get: async (url, config) => {
        const fullUrl = config?.params ? `${url}?${new URLSearchParams(config.params)}` : url;
        const response = await fetch(fullUrl);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        // Обработка 204 No Content
        if (response.status === 204) return { data: null };
        return { data: await response.json() };
    },
    post: async (url, data, config) => {
        const options = {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: data ? JSON.stringify(data) : '{}'
        };
        const fullUrl = config?.params ? `${url}?${new URLSearchParams(config.params)}` : url;
        const response = await fetch(fullUrl, options);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        // Обработка 204 No Content
        if (response.status === 204) return { data: null };
        return { data: await response.json() };
    },
    put: async (url, data, config) => {
        const options = {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: data ? JSON.stringify(data) : null
        };
        const fullUrl = config?.params ? `${url}?${new URLSearchParams(config.params)}` : url;
        const response = await fetch(fullUrl, options);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        // Обработка 204 No Content
        if (response.status === 204) return { data: null };
        return { data: await response.json() };
    },
    delete: async (url) => {
        const response = await fetch(url, { method: 'DELETE' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        // Обработка 204 No Content - пустой ответ
        if (response.status === 204) {
            return { data: null };
        }
        const text = await response.text();
        // Проверяем, что текст не пустой перед парсингом
        if (!text || text.trim() === '') {
            return { data: null };
        }
        try {
            return { data: JSON.parse(text) };
        } catch (e) {
            console.warn('Failed to parse DELETE response as JSON:', text);
            return { data: null };
        }
    }
};

// Глобальные переменные
let allEmployees = [];
let allSkills = [];
let currentFilters = { status: '', assigned_id: '' };

// === ИНИЦИАЛИЗАЦИЯ ===
document.addEventListener('DOMContentLoaded', () => {
    console.log('=== TASKS PAGE LOADED ===');
    loadData();
});

// === ЗАГРУЗКА ДАННЫХ ===
async function loadData() {
    try {
        const [empResponse, skillsResponse] = await Promise.all([
            axios.get('/api/v1/employees/available'),
            axios.get('/api/v1/skills')
        ]);

        allEmployees = empResponse.data;
        allSkills = skillsResponse.data;

        console.log('Сотрудники загружены:', allEmployees.length);
        console.log('Навыки загружены:', allSkills.length);

        populateSkillsDropdown();
        populateAssigneeFilter();
        loadUnassignedTasks();
        loadAssignedTasks();
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
    }
}

// === ФУНКЦИИ ФИЛЬТРОВ ===
async function applyFilters() {
    console.log('Применение фильтров...');
    currentFilters.status = document.getElementById('status-filter').value;
    currentFilters.assigned_id = document.getElementById('assignee-filter').value;

    const hasFilters = currentFilters.status || currentFilters.assigned_id;
    const unassignedSection = document.getElementById('unassigned-section');
    const assignedSection = document.getElementById('assigned-section');
    const filteredSection = document.getElementById('filtered-results-section');

    if (hasFilters) {
        if (filteredSection) filteredSection.style.display = 'block';
        if (unassignedSection) unassignedSection.style.display = 'none';
        if (assignedSection) assignedSection.style.display = 'none';
        await loadFilteredTasks();
    } else {
        if (filteredSection) filteredSection.style.display = 'none';
        if (unassignedSection) unassignedSection.style.display = 'block';
        if (assignedSection) assignedSection.style.display = 'block';
        loadUnassignedTasks();
        loadAssignedTasks();
    }
}

function resetFilters() {
    document.getElementById('status-filter').value = '';
    document.getElementById('assignee-filter').value = '';
    currentFilters = { status: '', assigned_id: '' };
    document.getElementById('filtered-tasks').innerHTML = '';
    loadUnassignedTasks();
    loadAssignedTasks();
}

// === ЗАГРУЗКА ЗАДАЧ ===
async function loadUnassignedTasks() {
    const response = await axios.get('/api/v1/tasks/unassigned');
    const tasks = response.data;
    const tbody = document.getElementById('unassigned-tasks');

    tbody.innerHTML = tasks.map(t => `
        <tr class="unassigned-row" data-task-id="${t.id}">
            <td>${t.id}</td>
            <td><strong>${t.title}</strong><div style="font-size: 12px; color: #666;">${t.description}</div></td>
            <td>
                <select onchange="updateTaskPriority('${t.id}', this.value)" class="priority-select">
                    <option value="critical" ${t.priority === 'critical' ? 'selected' : ''}>CRITICAL</option>
                    <option value="high" ${t.priority === 'high' ? 'selected' : ''}>HIGH</option>
                    <option value="medium" ${t.priority === 'medium' ? 'selected' : ''}>MEDIUM</option>
                    <option value="low" ${t.priority === 'low' ? 'selected' : ''}>LOW</option>
                </select>
            </td>
            <td>
                <select multiple onchange="updateTaskSkills('${t.id}', this.selectedOptions)" class="skills-select">
                    ${allSkills.map(s => `
                        <option value="${s.id}" ${Object.keys(t.required_skills).includes(s.id) ? 'selected' : ''}>
                            ${s.name}
                        </option>
                    `).join('')}
                </select>
            </td>
            <td>
                <input type="number" value="${t.estimated_effort}"
                       onchange="updateTaskEffort('${t.id}', this.value)"
                       class="effort-input" min="0.5" step="0.5">
            </td>
            <td>${formatDate(t.created_at)}</td>      <!-- ФОРМАТИРУЕМ ДАТУ -->
            <td>${formatDate(t.deadline)}</td>        <!-- ФОРМАТИРУЕМ ДАТУ -->
            <td class="actions-column">
                <select onchange="assignTask('${t.id}', this.value)" class="assignee-select">
                    <option value="">-- Назначить --</option>
                    ${allEmployees.map(e => `<option value="${e.id}">${e.name} (${e.type})</option>`).join('')}
                </select>
            </td>
            <td class="actions-column">
                <select onchange="handleUnassignedAction('${t.id}', this.value)" class="action-select">
                    <option value="">-- Действие --</option>
                    <option value="decompose">🔀 Декомпозировать</option>
                    <option value="delete">🗑️ Удалить</option>
                </select>
            </td>
        </tr>
    `).join('');
}

async function loadAssignedTasks() {
    console.log('Загрузка распределенных задач...');
    try {
        const response = await axios.get('/api/v1/tasks/');
        const allTasks = response.data;
        const assignedTasks = allTasks.filter(t => t.assigned_id);
        const tbody = document.getElementById('assigned-tasks');

        tbody.innerHTML = assignedTasks.map(t => {
            const emp = allEmployees.find(e => e.id === t.assigned_id);
            const assigneeName = emp ? `${emp.name} (${emp.type})` : t.assigned_id;

            return `
                <tr class="assigned-row ${t.status}" data-task-id="${t.id}">
                    <td>${t.id}</td>
                    <td><strong>${t.title}</strong><div style="font-size: 12px; color: #666;">${t.description || ''}</div></td>
                    <td>
                        <select class="assignee-select" onchange="updateAssignee('${t.id}', this.value)">
                            <option value="">-- Снять --</option>
                            ${allEmployees.map(e =>
                                `<option value="${e.id}" ${e.id === t.assigned_id ? 'selected' : ''}>
                                    ${e.type === 'digital' ? '🤖' : '👤'} ${e.name}
                                </option>`
                            ).join('')}
                        </select>
                    </td>
                    <td class="${String(t.priority).toLowerCase()}">
                        <select onchange="updatePriority('${t.id}', this.value)" style="font-size: 12px;">
                            <option value="CRITICAL" ${t.priority === 'CRITICAL' ? 'selected' : ''}>CRITICAL</option>
                            <option value="HIGH" ${t.priority === 'HIGH' ? 'selected' : ''}>HIGH</option>
                            <option value="MEDIUM" ${t.priority === 'MEDIUM' ? 'selected' : ''}>MEDIUM</option>
                            <option value="LOW" ${t.priority === 'LOW' ? 'selected' : ''}>LOW</option>
                        </select>
                    </td>
                    <td>
                        <select class="status-select" onchange="updateStatus('${t.id}', this.value)">
                            <option value="backlog" ${t.status === 'backlog' ? 'selected' : ''}>BACKLOG</option>
                            <option value="planned" ${t.status === 'planned' ? 'selected' : ''}>PLANNED</option>
                            <option value="in_progress" ${t.status === 'in_progress' ? 'selected' : ''}>IN_PROGRESS</option>
                            <option value="review" ${t.status === 'review' ? 'selected' : ''}>REVIEW</option>
                            <option value="done" ${t.status === 'done' ? 'selected' : ''}>DONE</option>
                            <option value="blocked" ${t.status === 'blocked' ? 'selected' : ''}>BLOCKED</option>
                        </select>
                    </td>
                    <td>${formatDate(t.assigned_at)}</td>     <!-- КОГДА НАЗНАЧЕНА -->
                    <td>${formatDate(t.deadline)}</td>        <!-- ДЕДЛАЙН -->

                    <td class="actions-column">
                        <button onclick="unassignTask('${t.id}')" class="edit-btn" title="Снять">Снять</button>
                        <button onclick="deleteTask('${t.id}')" class="delete-btn" title="Удалить">🗑️</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Ошибка загрузки распределенных задач:', error);
    }
}

async function loadFilteredTasks() {
    console.log('Загрузка отфильтрованных задач...');
    try {
        const params = {};
        if (currentFilters.status) params.status = currentFilters.status;
        if (currentFilters.assigned_id) params.assigned_id = currentFilters.assigned_id;

        const response = await axios.get('/api/v1/tasks/filtered', { params });
        const tasks = response.data;
        const tbody = document.getElementById('filtered-tasks');

        if (!tasks || tasks.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px;">Нет задач по фильтру</td></tr>';
            return;
        }

        tbody.innerHTML = tasks.map(t => {
            const emp = allEmployees.find(e => e.id === t.assigned_id);
            const assigneeName = emp ? `${emp.name} (${emp.type})` : '⚪ Не назначен';

            return `
                <tr class="assigned-row ${t.status}" data-task-id="${t.id}">
                    <td>${t.id}</td>
                    <td><strong>${t.title}</strong><div style="font-size: 12px; color: #666;">${t.description || ''}</div></td>
                    <td>
                        <select class="assignee-select" onchange="updateAssignee('${t.id}', this.value)">
                            <option value="">-- Снять --</option>
                            ${allEmployees.map(e =>
                                `<option value="${e.id}" ${e.id === t.assigned_id ? 'selected' : ''}>
                                    ${e.type === 'digital' ? '🤖' : '👤'} ${e.name}
                                </option>`
                            ).join('')}
                        </select>
                    </td>
                    <td class="${String(t.priority).toLowerCase()}">${t.priority}</td>
                    <td>${t.status}</td>
                    <td class="actions-column">
                        <button onclick="unassignTask('${t.id}')" class="edit-btn">Снять</button>
                        <button onclick="deleteTask('${t.id}')" class="delete-btn">🗑️</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Ошибка загрузки отфильтрованных задач:', error);
    }
}

// === ОПЕРАЦИИ С ЗАДАЧАМИ ===
async function assignTask(taskId, employeeId) {
    if (!employeeId) return;
    try {
        await axios.put(`/api/v1/tasks/${taskId}/assign`, {}, { params: { employee_id: employeeId } });
        loadData();
    } catch (error) {
        console.error('Ошибка назначения:', error);
    }
}

async function unassignTask(taskId) {
    try {
        await axios.put(`/api/v1/tasks/${taskId}/unassign`);
        loadData();
    } catch (error) {
        console.error('Ошибка снятия:', error);
    }
}

async function updateAssignee(taskId, employeeId) {
    const row = document.querySelector(`tr[data-task-id="${taskId}"]`);
    row.classList.add('updating');

    try {
        await axios.put(`/api/v1/tasks/${taskId}/assignee`, {}, {
            params: { employee_id: employeeId }
        });

        row.classList.remove('updating');
        row.classList.add('updated');

        // Обновляем таблицы через 0.5 сек
        setTimeout(() => {
            loadData();
            row.classList.remove('updated');
        }, 500);

    } catch (error) {
        row.classList.remove('updating');
        alert('Ошибка: ' + error.message);
    }
}

async function updatePriority(taskId, priority) {
    try {
        await axios.put(`/api/v1/tasks/${taskId}/priority`, {}, { params: { priority: priority } });
    } catch (error) {
        console.error('Ошибка обновления приоритета:', error);
    }
}

async function updateStatus(taskId, status) {
    // Убедитесь, что taskId — это строка, а не DOM-элемент
    console.log('Обновление статуса задачи:', taskId, status);

    try {
        const response = await axios.put(
            `/api/v1/tasks/${taskId}/status`,
            {},
            { params: { status: status } }
        );
        console.log('Статус обновлен:', response.data);
    } catch (error) {
        console.error('Ошибка обновления статуса:', error);
        alert('Не удалось обновить статус задачи');
    }
}

async function deleteTask(taskId) {
    if (!confirm(`Удалить задачу ${taskId}?`)) return;
    try {
        const row = document.querySelector(`tr[data-task-id="${taskId}"]`);
        if (row) {
            row.style.opacity = '0.5';
            row.style.transition = 'opacity 0.3s';
        }
        
        await axios.delete(`/api/v1/tasks/${taskId}`);
        
        // Удаляем строку из DOM
        if (row) {
            row.remove();
        }
        console.log(`✅ Задача ${taskId} удалена`);
    } catch (error) {
        console.error('❌ Ошибка удаления:', error);
        alert('Ошибка при удалении задачи: ' + error.message);
        // Восстанавливаем строку если ошибка
        const row = document.querySelector(`tr[data-task-id="${taskId}"]`);
        if (row) {
            row.style.opacity = '1';
        }
    }
}
// Обновление приоритета
async function updateTaskPriority(taskId, priority) {
    try {
        await axios.put(`/api/v1/tasks/${taskId}/priority`, {}, {
            params: { priority: priority }
        });
        console.log(`✅ Приоритет задачи ${taskId} обновлен`);
    } catch (error) {
        console.error('❌ Ошибка обновления приоритета:', error);
        alert('Ошибка обновления приоритета');
    }
}

// Обновление навыков
async function updateTaskSkills(taskId, selectedOptions) {
    const skills = {};
    for (let option of selectedOptions) {
        skills[option.value] = 3; // Уровень навыка
    }

    try {
        await axios.put(`/api/v1/tasks/${taskId}/skills`, skills); // Передаем объект напрямую
        console.log(`✅ Навыки задачи ${taskId} обновлены`);
    } catch (error) {
        console.error('❌ Ошибка обновления навыков:', error);
        alert('Ошибка обновления навыков');
    }
}

// Обновление оценки
async function updateTaskEffort(taskId, effort) {
    try {
        await axios.put(`/api/v1/tasks/${taskId}/effort`, {}, {
            params: { effort: parseFloat(effort) }
        });
        console.log(`✅ Оценка задачи ${taskId} обновлена`);
    } catch (error) {
        console.error('❌ Ошибка обновления оценки:', error);
        alert('Ошибка обновления оценки');
    }
}

// Обработка действий в нераспределенных задачах
async function handleUnassignedAction(taskId, action) {
    if (!action) return;

    switch(action) {
        case 'assign':
            // Открываем модальное окно или select для выбора сотрудника
            const employeeId = prompt('Введите ID сотрудника для назначения:');
            if (employeeId) {
                await assignTask(taskId, employeeId);
            }
            break;

        case 'decompose':
            if (confirm(`Декомпозировать задачу ${taskId} через LLM?`)) {
                await decomposeTask(taskId);
            }
            break;

        case 'delete':
            if (confirm(`Удалить задачу ${taskId}?`)) {
                await deleteTask(taskId);
            }
            break;
    }

    // Сбрасываем select
    document.querySelector(`tr[data-task-id="${taskId}"] .action-select`).value = '';
}

// Декомпозиция задачи через LLM
async function decomposeTask(taskId) {
    console.log('=== decomposeTask вызвана ===');
    console.log('Task ID:', taskId);
    
    try {
        console.log('Отправка POST запроса на /api/v1/tasks/' + taskId + '/decompose');
        const response = await axios.post(`/api/v1/tasks/${taskId}/decompose`, {}, {
            params: { max_subtasks: 5 }
        });
        console.log('Ответ сервера:', response.data);
        
        const subtasks = response.data.subtasks;
        alert(`✅ Задача декомпозирована на ${subtasks.length} подзадач`);
        loadData(); // Обновляем списки
    } catch (error) {
        console.error('❌ Ошибка декомпозиции:', error);
        alert('Ошибка при декомпозиции задачи: ' + error.message);
    }
}

// Перераспределение задач через линейное программирование
async function redistributeTasks() {
    console.log('=== redistributeTasks вызвана ===');
    
    if (!confirm('Перераспределить все нераспределенные задачи оптимально?')) return;

    try {
        console.log('Отправка POST запроса на /api/v1/planning/redistribute');
        const response = await axios.post('/api/v1/planning/redistribute', {}, {
            params: { days: 14 }
        });
        console.log('Ответ сервера:', response.data);
        
        const result = response.data;
        alert(`✅ Перераспределено ${result.saved_assignments} задач`);
        loadData(); // Обновляем все таблицы
    } catch (error) {
        console.error('❌ Ошибка перераспределения:', error);
        alert('Ошибка при перераспределении задач: ' + error.message);
    }
}
// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function populateSkillsDropdown() {
    const select = document.getElementById('task_skills_select');
    if (!select) return;
    select.innerHTML = allSkills.map(s =>
    `<option value="${s.id}">${s.name} (${s.category})</option>`
    ).join('');
}

function populateAssigneeFilter() {
    const select = document.getElementById('assignee-filter');
    if (!select) return;

    let html = '<option value="">Все исполнители</option>';
    html += '<option value="unassigned">⚪ Неназначенные</option>';

    allEmployees.forEach(e => {
        const icon = e.type === 'digital' ? '🤖' : '👤';
        html += `<option value="${e.id}">${icon} ${e.name}</option>`;
    });

    select.innerHTML = html;
}

// === ОБРАБОТКА ФОРМЫ ===
document.getElementById('create-task-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const skills = {};
    const selected = document.getElementById('task_skills_select').selectedOptions;
    for (let option of selected) {
        skills[option.value] = 3;
    }

    const taskData = {
        id: document.getElementById('task_id').value,
        title: document.getElementById('task_title').value,
        description: document.getElementById('task_description').value,
        required_skills: skills,
        priority: document.getElementById('task_priority').value,
        estimated_effort: parseFloat(document.getElementById('task_effort').value),
        deadline: document.getElementById('task_deadline').value || null
    };

    try {
        const response = await fetch('/api/v1/tasks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(taskData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка создания задачи');
        }

        document.getElementById('create-result').innerHTML = '<span style="color: green;">✅ Задача создана!</span>';
        document.getElementById('create-task-form').reset();
        loadData(); // Обновляем списки задач
    } catch (error) {
        console.error('Критическая ошибка:', error);
        document.getElementById('create-result').innerHTML = `<span style="color: red;">❌ Ошибка: ${error.message}</span>`;
    }
});

// Добавьте в tasks.js
document.getElementById('task_id').addEventListener('blur', async function() {
    const taskId = this.value;
    if (!taskId) return;

    try {
        const response = await fetch(`/api/v1/tasks/${taskId}`);
        if (response.ok) {
            // Задача существует
            document.getElementById('task_id').style.borderColor = 'red';
            document.getElementById('create-result').innerHTML =
            '<span style="color: red;">⚠️ Задача с таким ID уже существует!</span>';
        } else {
            document.getElementById('task_id').style.borderColor = 'green';
            document.getElementById('create-result').innerHTML = '';
        }
    } catch (e) {
        // Игнорируем ошибки проверки
    }
});