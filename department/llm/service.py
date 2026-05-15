"""
Сервис интеграции с LLM для декомпозиции задач и прогнозирования.
Поддерживает LM Studio API (OpenAI-совместимый).
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from department.models.task import Task
from department.rag.retriever import TaskRetriever, RetrievedTask


@dataclass
class ForecastPrediction:
    """Результат прогнозирования LLM"""
    task_id: str
    predicted_effort_hours: float
    confidence: float  # 0.0 - 1.0
    reasoning: str
    similar_tasks_used: List[RetrievedTask] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "predicted_effort_hours": self.predicted_effort_hours,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "risk_factors": self.risk_factors,
            "created_at": self.created_at.isoformat(),
            "similar_tasks_count": len(self.similar_tasks_used)
        }


class LLMService:
    """
    Сервис работы с LLM через LM Studio API.
    
    Поддерживает:
    - Декомпозицию задач
    - Прогнозирование времени выполнения (с RAG)
    - Анализ рисков
    """
    
    DEFAULT_LM_STUDIO_URL = "http://localhost:1234/v1"
    DEFAULT_MODEL = "local-model"
    DEFAULT_TIMEOUT = 320  # секунд
    
    def __init__(
        self,
        lm_studio_url: str = DEFAULT_LM_STUDIO_URL,
        model_name: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
        rag_retriever: Optional[TaskRetriever] = None
    ):
        """
        Инициализация LLM сервиса.
        
        Args:
            lm_studio_url: URL LM Studio API
            model_name: Название модели
            timeout: Таймаут запроса в секундах
            rag_retriever: RAG retriever для контекста
        """
        self.lm_studio_url = lm_studio_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.rag_retriever = rag_retriever or TaskRetriever()
    
    def _make_chat_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1024
    ) -> Optional[str]:
        """
        Отправить запрос к LM Studio Chat API.
        
        Args:
            messages: Список сообщений в формате OpenAI
            temperature: Температура генерации (0.1 для детерминированных ответов)
            max_tokens: Максимум токенов
            
        Returns:
            Текст ответа или None при ошибке
        """
        if not REQUESTS_AVAILABLE:
            print("Error: requests library not available")
            return None
        
        try:
            response = requests.post(
                f"{self.lm_studio_url}/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                },
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"].get("content", "")
                
                # Если content пустой, пробуем reasoning_content (для Qwen и подобных)
                if not content:
                    reasoning = data["choices"][0]["message"].get("reasoning_content", "")
                    if reasoning:
                        print(f"Using reasoning_content ({len(reasoning)} chars)")
                        content = reasoning
                
                print(f"LLM response length: {len(content)} chars")
                return content
            else:
                print(f"LM Studio API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"LM Studio request timeout ({self.timeout}s)")
            return None
        except Exception as e:
            print(f"LM Studio request error: {e}")
            return None
    
    def decompose_task_sync(self, task: Task, max_subtasks: int = 5) -> List[Dict[str, Any]]:
        """
        Декомпозировать задачу на подзадачи через LLM.
        
        Args:
            task: Задача для декомпозиции
            max_subtasks: Максимальное количество подзадач
            
        Returns:
            Список подзадач с title, description, effort
        """
        prompt = f"""Ты эксперт по декомпозиции задач. Разбей следующую задачу на {max_subtasks} или меньше подзадач.

Задача: {task.title}
Описание: {task.description}
Требуемые навыки: {task.required_skills}
Зависимости: {task.dependencies}

Для каждой подзадачи укажи:
1. Краткое название
2. Описание (1-2 предложения)
3. Оценку трудоемкости в часах

Верни ответ в формате JSON массива:
[
    {{"title": "...", "description": "...", "estimated_effort": 4.0}},
    ...
]

Только JSON, без дополнительного текста."""

        messages = [
            {"role": "system", "content": "Ты помощник для декомпозиции задач. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self._make_chat_request(messages, temperature=0.1)
        
        if response_text:
            try:
                print(f"Response text (first 500 chars): {response_text[:500]}")
                
                # Пытаемся найти JSON в ответе
                start_idx = response_text.find("[")
                end_idx = response_text.rfind("]") + 1
                
                print(f"JSON bounds: start={start_idx}, end={end_idx}")
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    print(f"Extracted JSON: {json_str}")
                    
                    # Очищаем экранирование для парсинга
                    json_str = json_str.replace('\\"', '"').replace('\\n', ' ').replace('\n', ' ')
                    print(f"Cleaned JSON: {json_str}")
                    
                    subtasks = json.loads(json_str)
                    print(f"Parsed {len(subtasks)} subtasks")
                    return subtasks
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                print(f"Failed JSON string: {json_str if 'json_str' in locals() else 'N/A'}")
        
        # Fallback: мок-ответ
        return self._mock_decompose(task, max_subtasks)
    
    def _mock_decompose(self, task: Task, max_subtasks: int) -> List[Dict[str, Any]]:
        """Резервная декомпозиция если LLM недоступен"""
        subtasks = []
        base_effort = task.estimated_effort / max_subtasks
        
        for i in range(min(3, max_subtasks)):
            subtasks.append({
                "title": f"{task.title} - Часть {i+1}",
                "description": f"Автоматически сгенерированная подзадача {i+1}",
                "estimated_effort": round(base_effort, 1)
            })
        
        return subtasks
    
    async def decompose_task(self, task: Task, max_subtasks: int = 5) -> List[Dict[str, Any]]:
        """Асинхронная версия декомпозиции"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.decompose_task_sync(task, max_subtasks)
        )
    
    def predict_effort_with_rag(
        self,
        task: Task,
        employee_type: str = "human",
        n_similar_tasks: int = 3
    ) -> ForecastPrediction:
        """
        Прогнозирование трудоемкости с использованием RAG.
        
        Args:
            task: Задача для прогнозирования
            employee_type: Тип сотрудника (human/digital)
            n_similar_tasks: Количество похожих задач для контекста
            
        Returns:
            ForecastPrediction с прогнозом
        """
        # 1. Находим похожие задачи в истории
        similar_tasks = self.rag_retriever.find_similar(
            task=task,
            n_results=n_similar_tasks,
            employee_type=employee_type
        )
        
        # 2. Формируем контекст для LLM
        context = self._build_rag_context(similar_tasks)
        
        # 3. Создаем промпт для прогнозирования
        prompt = self._build_forecast_prompt(task, context, employee_type)
        
        messages = [
            {"role": "system", "content": self._get_forecast_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        # 4. Запрашиваем прогноз у LLM
        response_text = self._make_chat_request(messages, temperature=0.1, max_tokens=512)
        
        # 5. Парсим ответ
        if response_text:
            forecast = self._parse_forecast_response(
                task.id, response_text, similar_tasks
            )
            if forecast:
                return forecast
        
        # 6. Fallback: прогноз на основе средней из похожих задач
        return self._fallback_forecast(task, similar_tasks, employee_type)
    
    def _build_rag_context(self, similar_tasks: List[RetrievedTask]) -> str:
        """Построить текстовый контекст из похожих задач"""
        if not similar_tasks:
            return "В истории нет похожих задач."
        
        lines = ["ИСТОРИЯ ПОХОЖИХ ЗАДАЧ:"]
        for i, st in enumerate(similar_tasks, 1):
            lines.append(
                f"{i}. Задача: \"{st.title}\"\n"
                f"   Описание: {st.description[:200]}...\n"
                f"   Фактическое время: {st.actual_duration_hours}ч\n"
                f"   Оценка: {st.actual_effort}ч\n"
                f"   Сходство: {st.similarity_score:.2f}\n"
            )
        
        return "\n".join(lines)
    
    def _build_forecast_prompt(
        self,
        task: Task,
        context: str,
        employee_type: str
    ) -> str:
        """Создать промпт для прогнозирования"""
        return f"""{context}

НОВАЯ ЗАДАЧА:
Название: {task.title}
Описание: {task.description}
Требуемые навыки: {task.required_skills}
Зависимости: {task.dependencies}
Приоритет: {task.priority}

Тип исполнителя: {employee_type}

На основе истории похожих задач, спрогнозируй:
1. Сколько часов займет выполнение новой задачи?
2. Какова уверенность в прогнозе (0.0-1.0)?
3. Какие факторы риска могут повлиять?

Верни ответ в формате JSON:
{{
    "predicted_hours": 8.5,
    "confidence": 0.8,
    "reasoning": "Краткое обоснование...",
    "risk_factors": ["риск 1", "риск 2"]
}}

Только JSON, без дополнительного текста."""
    
    def _get_forecast_system_prompt(self) -> str:
        """Системный промпт для прогнозирования"""
        return """Ты эксперт по оценке трудоемкости задач в производственном подразделении.
Твоя задача - анализировать исторические данные и давать точные прогнозы.
Отвечай ТОЛЬКО в формате JSON, без дополнительного текста."""
    
    def _parse_forecast_response(
        self,
        task_id: str,
        response_text: str,
        similar_tasks: List[RetrievedTask]
    ) -> Optional[ForecastPrediction]:
        """Распарсить ответ LLM и вернуть ForecastPrediction"""
        try:
            # Пытаемся найти JSON в ответе
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                data = json.loads(json_str)
                
                return ForecastPrediction(
                    task_id=task_id,
                    predicted_effort_hours=float(data.get("predicted_hours", 8)),
                    confidence=float(data.get("confidence", 0.5)),
                    reasoning=data.get("reasoning", ""),
                    similar_tasks_used=similar_tasks,
                    risk_factors=data.get("risk_factors", [])
                )
        except json.JSONDecodeError as e:
            print(f"Forecast JSON parse error: {e}")
        
        return None
    
    def _fallback_forecast(
        self,
        task: Task,
        similar_tasks: List[RetrievedTask],
        employee_type: str
    ) -> ForecastPrediction:
        """Резервный прогноз на основе статистики"""
        if similar_tasks:
            # Средняя из похожих задач
            avg_effort = sum(st.actual_effort for st in similar_tasks) / len(similar_tasks)
            avg_similarity = sum(st.similarity_score for st in similar_tasks) / len(similar_tasks)
            
            return ForecastPrediction(
                task_id=task.id,
                predicted_effort_hours=round(avg_effort, 1),
                confidence=round(avg_similarity * 0.9, 2),
                reasoning="Прогноз на основе средней трудоемкости похожих задач",
                similar_tasks_used=similar_tasks,
                risk_factors=["Недостаточно данных для точного прогноза"]
            )
        
        # Если нет похожих задач - используем базовую оценку
        return ForecastPrediction(
            task_id=task.id,
            predicted_effort_hours=task.estimated_effort,
            confidence=0.3,
            reasoning="Прогноз на основе базовой оценки (нет похожих задач в истории)",
            similar_tasks_used=[],
            risk_factors=["Нет исторических данных", "Высокая неопределенность"]
        )
    
    async def predict_effort_async(
        self,
        task: Task,
        employee_type: str = "human"
    ) -> ForecastPrediction:
        """Асинхронная версия прогнозирования"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.predict_effort_with_rag(task, employee_type)
        )
    
    async def analyze_risks(self, task: Task) -> List[str]:
        """Проанализировать риски задачи через LLM"""
        prompt = f"""Проанализируй риски для задачи:
Название: {task.title}
Описание: {task.description}
Навыки: {task.required_skills}
Зависимости: {task.dependencies}

Перечисли 3-5 основных рисков в формате JSON массива строк:
["риск 1", "риск 2", "риск 3"]

Только JSON."""

        messages = [
            {"role": "system", "content": "Ты эксперт по анализу рисков. Отвечай только JSON."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self._make_chat_request(messages, temperature=0.2)
        
        if response_text:
            try:
                start_idx = response_text.find("[")
                end_idx = response_text.rfind("]") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    return json.loads(response_text[start_idx:end_idx])
            except:
                pass
        
        return ["Высокая сложность", "Недостаточно данных"]


# Глобальный экземпляр по умолчанию
llm_service = LLMService()