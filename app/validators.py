"""Валидация входных данных."""

from datetime import datetime, timezone
from typing import Optional

from .constants import (
    MAX_PET_NAME_LENGTH,
    MAX_BREED_LENGTH,
    MAX_ENTRY_TEXT_LENGTH,
)


class ValidationError(Exception):
    """Ошибка валидации данных."""
    pass


def validate_pet_name(name: str) -> str:
    """
    Валидация имени питомца.
    
    Args:
        name: Имя питомца
        
    Returns:
        Очищенное имя
        
    Raises:
        ValidationError: Если имя невалидно
    """
    name = name.strip()
    
    if not name:
        raise ValidationError("Имя не может быть пустым.")
    
    if len(name) > MAX_PET_NAME_LENGTH:
        raise ValidationError(
            f"Имя слишком длинное (максимум {MAX_PET_NAME_LENGTH} символов)."
        )
    
    # Проверка на опасные символы для HTML
    if "<" in name or ">" in name:
        raise ValidationError("Имя содержит недопустимые символы.")
    
    return name


def validate_breed(breed: Optional[str]) -> Optional[str]:
    """
    Валидация породы питомца.
    
    Args:
        breed: Порода питомца (может быть None)
        
    Returns:
        Очищенная порода или None
        
    Raises:
        ValidationError: Если порода невалидна
    """
    if breed is None:
        return None
    
    breed = breed.strip()
    
    if not breed:
        return None
    
    if len(breed) > MAX_BREED_LENGTH:
        raise ValidationError(
            f"Порода слишком длинная (максимум {MAX_BREED_LENGTH} символов)."
        )
    
    if "<" in breed or ">" in breed:
        raise ValidationError("Порода содержит недопустимые символы.")
    
    return breed


def validate_entry_text(text: str) -> str:
    """
    Валидация текста записи.
    
    Args:
        text: Текст записи
        
    Returns:
        Очищенный текст
        
    Raises:
        ValidationError: Если текст невалиден
    """
    text = text.strip()
    
    if not text:
        raise ValidationError("Текст записи не может быть пустым.")
    
    if len(text) > MAX_ENTRY_TEXT_LENGTH:
        raise ValidationError(
            f"Текст слишком длинный (максимум {MAX_ENTRY_TEXT_LENGTH} символов)."
        )
    
    return text


def validate_date(date_str: str) -> datetime:
    """
    Валидация даты в формате YYYY-MM-DD.
    
    Args:
        date_str: Строка с датой
        
    Returns:
        Объект datetime
        
    Raises:
        ValidationError: Если дата невалидна
    """
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except ValueError:
        raise ValidationError(
            "Не удалось распознать дату. Введите в формате YYYY-MM-DD, например 2025-12-01."
        )
    
    # Проверка, что дата не в будущем (с запасом в 1 день на случай проблем с часовыми поясами)
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    max_future_date = now + timedelta(days=1)
    
    if dt > max_future_date:
        raise ValidationError("Дата не может быть в будущем.")
    
    # Проверка на разумные границы (не раньше 1900 года)
    min_date = datetime(1900, 1, 1)
    if dt < min_date:
        raise ValidationError("Дата слишком старая (минимум 1900 год).")
    
    return datetime(dt.year, dt.month, dt.day)


def sanitize_html(text: str) -> str:
    """
    Базовая санитизация HTML (замена опасных символов).
    
    Args:
        text: Текст для санитизации
        
    Returns:
        Санитизированный текст
    """
    return (
        text.replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("&", "&amp;")
    )

