"""
RAG (Retrieval-Augmented Generation) модуль для подразделения.
Использует векторную базу данных ChromaDB для хранения и поиска истории задач.
"""

from department.rag.vector_store import VectorStore
from department.rag.embeddings import EmbeddingService
from department.rag.retriever import TaskRetriever, RetrievedTask

__all__ = [
    "VectorStore",
    "EmbeddingService",
    "TaskRetriever",
    "RetrievedTask"
]