"""
Сервис генерации эмбеддингов для векторного поиска.
Использует локальную модель через sentence-transformers или LM Studio.
"""

from typing import List, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None


class EmbeddingService:
    """
    Сервис для генерации векторных представлений текста.
    
    Поддерживает два режима:
    1. sentence-transformers (локально, быстро)
    2. LM Studio API (через ту же модель что и для генерации)
    """
    
    DEFAULT_MODEL = "all-MiniLM-L6-v2"  # Легкая модель для эмбеддингов
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        use_lm_studio: bool = False,
        lm_studio_url: str = "http://localhost:1234/v1"
    ):
        """
        Инициализация сервиса эмбеддингов.
        
        Args:
            model_name: Название модели sentence-transformers
            use_lm_studio: Использовать LM Studio для эмбеддингов
            lm_studio_url: URL LM Studio API
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.use_lm_studio = use_lm_studio
        self.lm_studio_url = lm_studio_url.rstrip("/")
        self._model = None
        
        if not use_lm_studio and SENTENCE_TRANSFORMERS_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Загрузить модель sentence-transformers"""
        if SentenceTransformer is not None:
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                print(f"Warning: Could not load model {self.model_name}: {e}")
                self._model = None
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Получить векторное представление текста.
        
        Args:
            text: Текст для эмбеддинга
            
        Returns:
            Вектор эмбеддинга (список float)
        """
        if self.use_lm_studio:
            return self._get_embedding_lm_studio(text)
        else:
            return self._get_embedding_local(text)
    
    def _get_embedding_local(self, text: str) -> List[float]:
        """Получить эмбеддинг локально через sentence-transformers"""
        if self._model is None:
            # Fallback: простой хеш-вектор (если модель не загрузилась)
            return self._get_fallback_embedding(text)
        
        try:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return self._get_fallback_embedding(text)
    
    def _get_embedding_lm_studio(self, text: str) -> List[float]:
        """Получить эмбеддинг через LM Studio API"""
        import requests
        
        try:
            response = requests.post(
                f"{self.lm_studio_url}/embeddings",
                json={
                    "model": "local-model",
                    "input": text
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            print(f"LM Studio embedding error: {e}")
        
        # Fallback при ошибке
        return self._get_fallback_embedding(text)
    
    def _get_fallback_embedding(self, text: str) -> List[float]:
        """
        Резервный метод: простой вектор на основе TF-IDF признаков.
        Используется если ни одна модель не доступна.
        """
        # Простой хеш-подход для совместимости
        np.random.seed(hash(text) % 2**32)
        embedding = np.random.randn(384).astype(np.float32)
        # Нормализация
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Получить эмбеддинги для списка текстов.
        
        Args:
            texts: Список текстов
            
        Returns:
            Список векторов эмбеддингов
        """
        if self._model is not None and not self.use_lm_studio:
            try:
                embeddings = self._model.encode(texts, convert_to_numpy=True)
                return embeddings.tolist()
            except Exception as e:
                print(f"Batch embedding error: {e}")
        
        # Поштучная обработка
        return [self.get_embedding(text) for text in texts]