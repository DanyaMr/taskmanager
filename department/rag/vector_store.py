"""
Векторное хранилище на основе ChromaDB для хранения истории задач.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import os
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

from department.rag.embeddings import EmbeddingService


class VectorStore:
    """
    Векторное хранилище для задач подразделения.
    
    Использует ChromaDB для хранения и поиска задач по семантической близости.
    Каждая задача сохраняется с эмбеддингом описания и метаданными.
    """
    
    COLLECTION_NAME = "task_history"
    DB_PATH = "department/rag/vector_db"
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Инициализация векторного хранилища.
        
        Args:
            persist_directory: Путь для сохранения базы (по умолчанию department/rag/vector_db)
            embedding_service: Сервис для генерации эмбеддингов
        """
        self.persist_directory = persist_directory or self.DB_PATH
        
        # Создаем директорию если не существует
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.embedding_service = embedding_service or EmbeddingService()
        self._client = None
        self._collection = None
        
        if CHROMADB_AVAILABLE:
            self._initialize_chroma()
        else:
            print("Warning: ChromaDB not available. Using in-memory fallback.")
            self._init_fallback()
    
    def _initialize_chroma(self):
        """Инициализация ChromaDB клиента"""
        try:
            # Persisted client
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Получаем или создаем коллекцию
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "History of completed tasks"}
            )
        except Exception as e:
            print(f"ChromaDB initialization error: {e}")
            self._init_fallback()
    
    def _init_fallback(self):
        """Резервное хранилище в памяти если ChromaDB недоступен"""
        self._memory_store: List[Dict[str, Any]] = []
    
    def add_task(
        self,
        task_id: str,
        title: str,
        description: str,
        actual_effort: float,
        actual_duration_hours: float,
        skills_used: List[str],
        employee_type: str,
        completed_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Добавить выполненную задачу в векторное хранилище.
        
        Args:
            task_id: ID задачи
            title: Заголовок задачи
            description: Описание задачи
            actual_effort: Фактическая трудоемкость (часы)
            actual_duration_hours: Фактическая длительность (часы)
            skills_used: Использованные навыки
            employee_type: Тип сотрудника (human/digital)
            completed_at: Дата завершения
            metadata: Дополнительные метаданные
            
        Returns:
            True если успешно добавлено
        """
        # Создаем текст для эмбеддинга (объединяем title и description)
        embedding_text = f"{title}: {description}"
        
        # Получаем эмбеддинг
        embedding = self.embedding_service.get_embedding(embedding_text)
        
        # Метаданные для поиска
        task_metadata = {
            "task_id": task_id,
            "title": title,
            "actual_effort": actual_effort,
            "actual_duration_hours": actual_duration_hours,
            "skills_used": ",".join(skills_used) if skills_used else "",
            "employee_type": employee_type,
            "completed_at": completed_at.isoformat() if completed_at else datetime.now().isoformat(),
            **(metadata or {})
        }
        
        if CHROMADB_AVAILABLE and self._collection is not None:
            try:
                self._collection.upsert(
                    ids=[task_id],
                    embeddings=[embedding],
                    metadatas=[task_metadata],
                    documents=[embedding_text]
                )
                return True
            except Exception as e:
                print(f"Error adding task to ChromaDB: {e}")
                return False
        else:
            # Fallback: хранение в памяти
            self._memory_store.append({
                "id": task_id,
                "embedding": embedding,
                "metadata": task_metadata,
                "document": embedding_text
            })
            return True
    
    def find_similar_tasks(
        self,
        query_text: str,
        n_results: int = 5,
        filter_by_skills: Optional[List[str]] = None,
        filter_by_employee_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Найти похожие задачи по тексту запроса.
        
        Args:
            query_text: Текст для поиска (описание новой задачи)
            n_results: Количество результатов
            filter_by_skills: Фильтр по навыкам
            filter_by_employee_type: Фильтр по типу сотрудника
            
        Returns:
            Список похожих задач с метаданными
        """
        # Получаем эмбеддинг запроса
        query_embedding = self.embedding_service.get_embedding(query_text)
        
        if CHROMADB_AVAILABLE and self._collection is not None:
            try:
                # Формируем where фильтр
                where_filter = None
                if filter_by_employee_type:
                    where_filter = {"employee_type": filter_by_employee_type}
                
                results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where_filter,
                    include=["metadatas", "documents", "distances"]
                )
                
                # Формируем результат
                similar_tasks = []
                if results and results['metadatas'] and results['metadatas'][0]:
                    for i, metadata in enumerate(results['metadatas'][0]):
                        task = {
                            **metadata,
                            "distance": results['distances'][0][i] if results['distances'] else 0,
                            "document": results['documents'][0][i] if results['documents'] else ""
                        }
                        
                        # Применяем фильтр по навыкам
                        if filter_by_skills:
                            task_skills = metadata.get("skills_used", "").split(",")
                            if not any(skill in task_skills for skill in filter_by_skills):
                                continue
                                
                        similar_tasks.append(task)
                
                return similar_tasks
                
            except Exception as e:
                print(f"Error searching in ChromaDB: {e}")
                return self._search_fallback(query_embedding, n_results, filter_by_skills, filter_by_employee_type)
        else:
            return self._search_fallback(query_embedding, n_results, filter_by_skills, filter_by_employee_type)
    
    def _search_fallback(
        self,
        query_embedding: List[float],
        n_results: int,
        filter_by_skills: Optional[List[str]],
        filter_by_employee_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Резервный поиск в памяти"""
        import numpy as np
        
        scored_tasks = []
        query_vec = np.array(query_embedding)
        
        for item in self._memory_store:
            # Применяем фильтры
            metadata = item["metadata"]
            
            if filter_by_employee_type and metadata.get("employee_type") != filter_by_employee_type:
                continue
                
            if filter_by_skills:
                task_skills = metadata.get("skills_used", "").split(",")
                if not any(skill in task_skills for skill in filter_by_skills):
                    continue
            
            # Вычисляем косинусное сходство
            item_vec = np.array(item["embedding"])
            similarity = np.dot(query_vec, item_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(item_vec))
            
            scored_tasks.append({
                **metadata,
                "distance": float(1 - similarity),  # distance = 1 - similarity
                "document": item["document"]
            })
        
        # Сортируем по сходству (меньше distance = лучше)
        scored_tasks.sort(key=lambda x: x["distance"])
        return scored_tasks[:n_results]
    
    def get_task_count(self) -> int:
        """Получить количество задач в хранилище"""
        if CHROMADB_AVAILABLE and self._collection is not None:
            return self._collection.count()
        return len(self._memory_store)
    
    def clear(self):
        """Очистить хранилище"""
        if CHROMADB_AVAILABLE and self._collection is not None:
            try:
                self._client.delete_collection(self.COLLECTION_NAME)
                self._collection = self._client.create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"description": "History of completed tasks"}
                )
            except Exception as e:
                print(f"Error clearing ChromaDB: {e}")
        self._memory_store = []
    
    def get_all_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить все задачи (для отладки)"""
        if CHROMADB_AVAILABLE and self._collection is not None:
            try:
                results = self._collection.get(
                    limit=limit,
                    include=["metadatas", "documents"]
                )
                return [
                    {**metadata, "document": doc}
                    for metadata, doc in zip(results.get("metadatas", []), results.get("documents", []))
                ]
            except Exception as e:
                print(f"Error getting all tasks: {e}")
        return self._memory_store[:limit]