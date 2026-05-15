"""
Модели чек-листов для контроля качества задач.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class ChecklistItemType(str, Enum):
    """Типы элементов чек-листа"""
    REQUIRED = "required"  # Обязательный
    OPTIONAL = "optional"  # Опциональный
    SAFETY = "safety"  # Безопасность
    QUALITY = "quality"  # Качество
    DOCUMENTATION = "documentation"  # Документация


class VerificationStatus(str, Enum):
    """Статусы проверки"""
    PENDING = "pending"  # Ожидает проверки
    PASSED = "passed"  # Пройдено
    FAILED = "failed"  # Не пройдено
    SKIPPED = "skipped"  # Пропущено


@dataclass
class ChecklistItem:
    """
    Элемент чек-листа требования.
    
    Attributes:
        id: Уникальный идентификатор
        title: Краткое название требования
        description: Подробное описание
        item_type: Тип требования
        is_mandatory: Обязательно ли для выполнения
        verification_criteria: Критерии проверки
    """
    id: str
    title: str
    description: str = ""
    item_type: ChecklistItemType = ChecklistItemType.REQUIRED
    is_mandatory: bool = True
    verification_criteria: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "item_type": self.item_type.value,
            "is_mandatory": self.is_mandatory,
            "verification_criteria": self.verification_criteria,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChecklistItem":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            item_type=ChecklistItemType(data.get("item_type", "required")),
            is_mandatory=data.get("is_mandatory", True),
            verification_criteria=data.get("verification_criteria", ""),
            metadata=data.get("metadata", {})
        )


@dataclass
class ChecklistVerification:
    """
    Результат проверки элемента чек-листа.
    
    Attributes:
        item_id: ID проверенного элемента
        status: Статус проверки
        verified_by: Кто проверил (ID сотрудника)
        verified_at: Время проверки
        comments: Комментарии проверяющего
        evidence: Ссылки на доказательства (файлы, скриншоты)
    """
    item_id: str
    status: VerificationStatus = VerificationStatus.PENDING
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    comments: str = ""
    evidence: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "status": self.status.value,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "comments": self.comments,
            "evidence": self.evidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChecklistVerification":
        verified_at = data.get("verified_at")
        if isinstance(verified_at, str):
            verified_at = datetime.fromisoformat(verified_at)
        
        return cls(
            item_id=data.get("item_id", ""),
            status=VerificationStatus(data.get("status", "pending")),
            verified_by=data.get("verified_by"),
            verified_at=verified_at,
            comments=data.get("comments", ""),
            evidence=data.get("evidence", [])
        )


@dataclass
class Checklist:
    """
    Чек-лист требований для задачи.
    
    Attributes:
        id: Уникальный идентификатор чек-листа
        task_id: ID связанной задачи
        name: Название чек-листа
        items: Список элементов
        verifications: Результаты проверок
        created_at: Дата создания
    """
    id: str
    task_id: str
    name: str = ""
    items: List[ChecklistItem] = field(default_factory=list)
    verifications: Dict[str, ChecklistVerification] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_item(self, item: ChecklistItem):
        """Добавить элемент в чек-лист"""
        self.items.append(item)
    
    def remove_item(self, item_id: str):
        """Удалить элемент из чек-листа"""
        self.items = [i for i in self.items if i.id != item_id]
        if item_id in self.verifications:
            del self.verifications[item_id]
    
    def verify_item(
        self,
        item_id: str,
        status: VerificationStatus,
        verified_by: str,
        comments: str = "",
        evidence: List[str] = None
    ) -> bool:
        """
        Отметить элемент как проверенный.
        
        Returns:
            True если элемент найден и обновлен
        """
        item = next((i for i in self.items if i.id == item_id), None)
        if not item:
            return False
        
        self.verifications[item_id] = ChecklistVerification(
            item_id=item_id,
            status=status,
            verified_by=verified_by,
            verified_at=datetime.now(),
            comments=comments,
            evidence=evidence or []
        )
        return True
    
    def get_verification_status(self, item_id: str) -> Optional[VerificationStatus]:
        """Получить статус проверки элемента"""
        if item_id in self.verifications:
            return self.verifications[item_id].status
        return None
    
    def is_item_verified(self, item_id: str) -> bool:
        """Проверить, пройден ли элемент"""
        status = self.get_verification_status(item_id)
        return status == VerificationStatus.PASSED
    
    def get_completion_stats(self) -> Dict[str, Any]:
        """Получить статистику выполнения чек-листа"""
        total = len(self.items)
        mandatory = [i for i in self.items if i.is_mandatory]
        verified = [i for i in self.items if i.id in self.verifications]
        passed = [
            i for i in self.items
            if i.id in self.verifications and self.verifications[i.id].status == VerificationStatus.PASSED
        ]
        failed = [
            i for i in self.items
            if i.id in self.verifications and self.verifications[i.id].status == VerificationStatus.FAILED
        ]
        mandatory_passed = [
            i for i in mandatory
            if i.id in self.verifications and self.verifications[i.id].status == VerificationStatus.PASSED
        ]
        
        return {
            "total_items": total,
            "mandatory_items": len(mandatory),
            "verified_count": len(verified),
            "passed_count": len(passed),
            "failed_count": len(failed),
            "mandatory_passed": len(mandatory_passed),
            "completion_rate": len(passed) / total if total > 0 else 0,
            "mandatory_completion_rate": len(mandatory_passed) / len(mandatory) if mandatory else 1.0
        }
    
    def is_complete(self) -> bool:
        """Проверить, завершен ли чек-лист (все обязательные элементы пройдены)"""
        stats = self.get_completion_stats()
        return stats["mandatory_completion_rate"] == 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "name": self.name,
            "items": [item.to_dict() for item in self.items],
            "verifications": {k: v.to_dict() for k, v in self.verifications.items()},
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "stats": self.get_completion_stats()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checklist":
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        checklist = cls(
            id=data.get("id", ""),
            task_id=data.get("task_id", ""),
            name=data.get("name", ""),
            created_at=created_at or datetime.now(),
            metadata=data.get("metadata", {})
        )
        
        for item_data in data.get("items", []):
            checklist.items.append(ChecklistItem.from_dict(item_data))
        
        for item_id, ver_data in data.get("verifications", {}).items():
            checklist.verifications[item_id] = ChecklistVerification.from_dict(ver_data)
        
        return checklist


# Предустановленные шаблоны чек-листов
TEMPLATE_CHECKLISTS = {
    "software_development": Checklist(
        id="template_software",
        task_id="",
        name="Шаблон: Разработка ПО",
        items=[
            ChecklistItem(
                id="code_review",
                title="Code Review",
                description="Код проверен другим разработчиком",
                item_type=ChecklistItemType.QUALITY,
                is_mandatory=True,
                verification_criteria="PR одобрен минимум 2 разработчиками"
            ),
            ChecklistItem(
                id="unit_tests",
                title="Unit Tests",
                description="Написаны unit-тесты для нового кода",
                item_type=ChecklistItemType.QUALITY,
                is_mandatory=True,
                verification_criteria="Coverage >= 80%"
            ),
            ChecklistItem(
                id="documentation",
                title="Документация",
                description="Обновлена документация",
                item_type=ChecklistItemType.DOCUMENTATION,
                is_mandatory=False,
                verification_criteria="README обновлен"
            ),
            ChecklistItem(
                id="security_scan",
                title="Security Scan",
                description="Проверка на уязвимости",
                item_type=ChecklistItemType.SAFETY,
                is_mandatory=True,
                verification_criteria="Нет критических уязвимостей"
            )
        ]
    ),
    "hardware_maintenance": Checklist(
        id="template_hardware",
        task_id="",
        name="Шаблон: Обслуживание оборудования",
        items=[
            ChecklistItem(
                id="safety_check",
                title="Проверка безопасности",
                description="Оборудование отключено и обесточено",
                item_type=ChecklistItemType.SAFETY,
                is_mandatory=True,
                verification_criteria="LOTO процедура выполнена"
            ),
            ChecklistItem(
                id="visual_inspection",
                title="Визуальный осмотр",
                description="Проверка на износ и повреждения",
                item_type=ChecklistItemType.QUALITY,
                is_mandatory=True,
                verification_criteria="Фотоотчет"
            ),
            ChecklistItem(
                id="functional_test",
                title="Функциональный тест",
                description="Проверка работы после обслуживания",
                item_type=ChecklistItemType.QUALITY,
                is_mandatory=True,
                verification_criteria="Все функции работают"
            ),
            ChecklistItem(
                id="maintenance_log",
                title="Журнал обслуживания",
                description="Запись в журнале обслуживания",
                item_type=ChecklistItemType.DOCUMENTATION,
                is_mandatory=True,
                verification_criteria="Запись с датой и подписью"
            )
        ]
    ),
    "general_task": Checklist(
        id="template_general",
        task_id="",
        name="Шаблон: Общая задача",
        items=[
            ChecklistItem(
                id="requirements_met",
                title="Требования выполнены",
                description="Все требования задачи выполнены",
                item_type=ChecklistItemType.QUALITY,
                is_mandatory=True,
                verification_criteria="Сверка с описанием задачи"
            ),
            ChecklistItem(
                id="stakeholder_approval",
                title="Согласование",
                description="Задача согласована с заказчиком",
                item_type=ChecklistItemType.DOCUMENTATION,
                is_mandatory=False
            )
        ]
    )
}


def get_template(template_name: str) -> Optional[Checklist]:
    """Получить шаблон чек-листа по названию"""
    import copy
    template = TEMPLATE_CHECKLISTS.get(template_name)
    if template:
        # Возвращаем копию шаблона
        return copy.deepcopy(template)
    return None