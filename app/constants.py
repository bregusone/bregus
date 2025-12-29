"""Константы для бота Pet Health Diary."""

from enum import Enum


class EntryType(str, Enum):
    """Типы записей в дневнике."""
    SYMPTOM = "symptom"
    VISIT = "visit"
    VACCINE = "vaccine"
    MEDS = "meds"
    OTHER = "other"


class PetSpecies(str, Enum):
    """Виды питомцев."""
    CAT = "cat"
    DOG = "dog"
    OTHER = "other"


# Ограничения для валидации
MAX_PET_NAME_LENGTH = 64
MAX_BREED_LENGTH = 64
MAX_ENTRY_TEXT_LENGTH = 2000
MAX_HISTORY_ITEMS_PER_PAGE = 10

# Интервалы для напоминаний (в днях)
VACCINE_REMINDER_INTERVALS = {
    "30": 30,   # 1 месяц
    "90": 90,   # 3 месяца
    "180": 180, # 6 месяцев
    "365": 365, # 1 год
}

# Интервал проверки напоминаний (в секундах)
REMINDERS_CHECK_INTERVAL = 60

# Периоды для сводки (в днях)
SUMMARY_PERIODS = [7, 30, 90]

# Маппинг типов записей на русские названия
ENTRY_TYPE_NAMES = {
    EntryType.SYMPTOM: "🤒 Симптом",
    EntryType.VISIT: "🏥 Визит",
    EntryType.VACCINE: "💉 Прививка",
    EntryType.MEDS: "💊 Лекарство",
    EntryType.OTHER: "📝 Другое",
}

# Маппинг видов питомцев на русские названия
SPECIES_NAMES = {
    PetSpecies.CAT: "Кот",
    PetSpecies.DOG: "Пёс",
    PetSpecies.OTHER: "Другое",
}

# Иконки для видов питомцев
SPECIES_ICONS = {
    PetSpecies.CAT: "🐱",
    PetSpecies.DOG: "🐶",
    PetSpecies.OTHER: "🐾",
}

