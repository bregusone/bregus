from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


MAIN_MENU_BUTTON_PETS = "🐾 Питомцы"
MAIN_MENU_BUTTON_ENTRY = "✏ Запись"
MAIN_MENU_BUTTON_HISTORY = "🕓 История"
MAIN_MENU_BUTTON_SUMMARY = "📊 Сводка"
MAIN_MENU_BUTTON_SETTINGS = "⚙ Настройки"


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=MAIN_MENU_BUTTON_PETS),
                KeyboardButton(text=MAIN_MENU_BUTTON_ENTRY),
            ],
            [
                KeyboardButton(text=MAIN_MENU_BUTTON_HISTORY),
                KeyboardButton(text=MAIN_MENU_BUTTON_SUMMARY),
            ],
            [KeyboardButton(text=MAIN_MENU_BUTTON_SETTINGS)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел…",
    )


def pets_list_kb(pets: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for pet_id, title in pets:
        builder.button(text=title, callback_data=f"pet:{pet_id}")
    builder.button(text="➕ Добавить питомца", callback_data="pets:add")
    builder.button(text="⬅ Назад", callback_data="pets:back")
    builder.adjust(1)
    return builder.as_markup()


def pet_card_kb(pet_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_active:
        builder.button(
            text="⭐ Сделать активным",
            callback_data=f"pet:set_active:{pet_id}",
        )
    builder.button(text="⬅ К списку", callback_data="pets:list")
    builder.adjust(1)
    return builder.as_markup()


def species_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🐱 Кот", callback_data="species:cat")
    builder.button(text="🐶 Пёс", callback_data="species:dog")
    builder.button(text="🐾 Другое", callback_data="species:other")
    builder.adjust(1)
    return builder.as_markup()


def breed_skip_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➡ Пропустить", callback_data="breed:skip")
    return builder.as_markup()


def entry_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🤒 Симптом", callback_data="entry:type:symptom")
    builder.button(text="🏥 Визит", callback_data="entry:type:visit")
    builder.button(text="💉 Прививка", callback_data="entry:type:vaccine")
    builder.button(text="💊 Лекарство", callback_data="entry:type:meds")
    builder.button(text="📝 Другое", callback_data="entry:type:other")
    builder.adjust(1)
    return builder.as_markup()


def entry_date_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Сегодня", callback_data="entry:date:today")
    builder.button(text="📆 Вчера", callback_data="entry:date:yesterday")
    builder.button(text="✏ Ввести дату", callback_data="entry:date:custom")
    builder.adjust(1)
    return builder.as_markup()


def summary_periods_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="7 дней", callback_data="summary:days:7")
    builder.button(text="30 дней", callback_data="summary:days:30")
    builder.button(text="90 дней", callback_data="summary:days:90")
    builder.adjust(3)
    return builder.as_markup()



