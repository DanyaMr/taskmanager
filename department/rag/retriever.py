"""
Retriever - компонент для поиска и извлечения похожих задач.
Использует векторное хранилище для семантического поиска.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from department.rag.vector_store import VectorStore
from department.rag.embeddings import EmbeddingService
from department.models.task import Task


@dataclass
class RetrievedTask:
    """Найденная похожая задача"""
    task_id: str
    title: str
    description: str
    actual_effort: float
    actual_duration_hours: float
    similarity_score: float  # 0.0 - 1.0 (1.0 = идентичная)
    skills_used: List[str] = field(default_factory=list)
    employee_type: str = "human"
    completed_at: Optional[str] = None


class TaskRetriever:
    """
    Компонент для поиска похожих задач в истории.
    
    Использует векторное хранилище для семантического поиска
    и возвращает задачи отсортированные по релевантности.
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Инициализация retriever'а.
        
        Args:
            vector_store: Векторное хранилище (создается новое если не указано)
            embedding_service: Сервис эмбеддингов
        """
        self.vector_store = vector_store or VectorStore(embedding_service=embedding_service)
        self.embedding_service = embedding_service or self.vector_store.embedding_service
    
    def find_similar(
        self,
        task: Task,
        n_results: int = 5,
        employee_type: Optional[str] = None
    ) -> List[RetrievedTask]:
        """
        Найти похожие задачи для данной задачи.
        
        Args:
            task: Задача для которой ищем похожие
            n_results: Количество результатов
            employee_type: Фильтр по типу сотрудника (human/digital)
            
        Returns:
            Список похожих задач
        """
        # Формируем поисковый запрос из title и description
        query_text = f"{task.title}: {task.description}"
        
        # Ищем в хранилище
        similar = self.vector_store.find_similar_tasks(
            query_text=query_text,
            n_results=n_results,
            filter_by_skills=list(task.required_skills.keys()) if task.required_skills else None,
            filter_by_employee_type=employee_type
        )
        
        # Конвертируем в RetrievedTask
        results = []
        for item in similar:
            # distance -> similarity (1 - distance)
            similarity = 1.0 - item.get("distance", 0)
            
            retrieved = RetrievedTask(
                task_id=item.get("task_id", ""),
                title=item.get("title", ""),
                description=item.get("document", ""),
                actual_effort=item.get("actual_effort", 0),
                actual_duration_hours=item.get("actual_duration_hours", 0),
                similarity_score=max(0, similarity),
                skills_used=item.get("skills_used", "").split(",") if item.get("skills_used") else [],
                employee_type=item.get("employee_type", "human"),
                completed_at=item.get("completed_at")
            )
            results.append(retrieved)
        
        return results
    
    def find_similar_by_text(
        self,
        query_text: str,
        n_results: int = 5,
        filter_by_skills: Optional[List[str]] = None
    ) -> List[RetrievedTask]:
        """
        Найти похожие задачи по произвольному тексту.
        
        Args:
            query_text: Текст для поиска
            n_results: Количество результатов
            filter_by_skills: Фильтр по навыкам
            
        Returns:
            Список похожих задач
        """
        similar = self.vector_store.find_similar_tasks(
            query_text=query_text,
            n_results=n_results,
            filter_by_skills=filter_by_skills,
            filter_by_employee_type=None
        )
        
        results = []
        for item in similar:
            similarity = 1.0 - item.get("distance", 0)
            retrieved = RetrievedTask(
                task_id=item.get("task_id", ""),
                title=item.get("title", ""),
                description=item.get("document", ""),
                actual_effort=item.get("actual_effort", 0),
                actual_duration_hours=item.get("actual_duration_hours", 0),
                similarity_score=max(0, similarity),
                skills_used=item.get("skills_used", "").split(",") if item.get("skills_used") else [],
                employee_type=item.get("employee_type", "human"),
                completed_at=item.get("completed_at")
            )
            results.append(retrieved)
        
        return results
    
    def add_completed_task(
        self,
        task_id: str,
        title: str,
        description: str,
        actual_effort: float,
        actual_duration_hours: float,
        skills_used: List[str],
        employee_type: str
    ) -> bool:
        """
        Добавить выполненную задачу в хранилище.
        
        Args:
            task_id: ID задачи
            title: Заголовок
            description: Описание
            actual_effort: Фактическая трудоемкость
            actual_duration_hours: Фактическая длительность
            skills_used: Использованные навыки
            employee_type: Тип сотрудника
            
        Returns:
            True если успешно
        """
        return self.vector_store.add_task(
            task_id=task_id,
            title=title,
            description=description,
            actual_effort=actual_effort,
            actual_duration_hours=actual_duration_hours,
            skills_used=skills_used,
            employee_type=employee_type
        )
    
    def get_context_for_llm(
        self,
        task: Task,
        n_results: int = 3
    ) -> str:
        """
        Сформировать контекст для LLM на основе похожих задач.
        
        Args:
            task: Задача для контекста
            n_results: Количество похожих задач
            
        Returns:
            Текстовый контекст для отправки в LLM
        """
        similar = self.find_similar(task, n_results=n_results)
        
        if not similar:
            return "Нет похожих задач в истории."
        
        lines = ["Похожие задачи из истории:"]
        for i, st in enumerate(similar, 1):
            lines.append(
                f"{i}. \"{st.title}\" - "
                f"выполнено за {st.actual_duration_hours}ч (оценка: {st.actual_effort}ч), "
                f"сходство: {st.similarity_score:.2f}"
            )
        
        return "\n".join(lines)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику хранилища"""
        return {
            "total_tasks": self.vector_store.get_task_count(),
            "embedding_service": self.embedding_service.__class__.__name__
        }