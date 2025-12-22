import asyncio
from contextlib import suppress
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from .config import load_settings
from .db import init_db, get_session
from .keyboards import (
    main_menu_kb,
    MAIN_MENU_BUTTON_PETS,
    MAIN_MENU_BUTTON_ENTRY,
    MAIN_MENU_BUTTON_HISTORY,
    MAIN_MENU_BUTTON_SUMMARY,
    MAIN_MENU_BUTTON_SETTINGS,
    pets_list_kb,
    pet_card_kb,
    species_kb,
    breed_skip_kb,
    entry_type_kb,
    entry_date_kb,
    summary_periods_kb,
)
from .models import User, Pet, Entry, Attachment, Reminder
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties


class AddPetStates(StatesGroup):
    name = State()
    species = State()
    breed = State()


class AddEntryStates(StatesGroup):
    type = State()
    date_choice = State()
    custom_date = State()
    text = State()


class AttachFilesStates(StatesGroup):
    adding = State()


class VaccineReminderStates(StatesGroup):
    choosing_vaccine = State()
    choosing_delay = State()
    custom_delay = State()


async def ensure_user(message: Message) -> User:
    assert message.from_user is not None
    telegram_id = message.from_user.id

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def cmd_start(message: Message) -> None:
    await ensure_user(message)
    text = (
        "Привет! Я бот-дневник здоровья питомцев 🐾\n\n"
        "С моей помощью вы можете вести записи о симптомах, визитах к врачу, "
        "прививках и лекарствах, а также смотреть сводку.\n\n"
        "Выберите раздел в меню ниже."
    )
    await message.answer(text, reply_markup=main_menu_kb())


async def cmd_help(message: Message) -> None:
    text = (
        "ℹ Помощь\n\n"
        "/start — начать работу и показать главное меню\n"
        "/help — показать эту подсказку\n"
        "/cancel — отменить текущий шаг и вернуться в главное меню\n\n"
        "Основная навигация — через кнопки в нижнем меню."
    )
    await message.answer(text, reply_markup=main_menu_kb())


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Сейчас нет активного действия. Используйте меню ниже.",
            reply_markup=main_menu_kb(),
        )
        return

    await state.clear()
    await message.answer(
        "Текущий ввод отменён. Выберите раздел в меню ниже.",
        reply_markup=main_menu_kb(),
    )


async def show_pets_menu(message: Message) -> None:
    """Выводит экран «Питомцы» со списком и активным питомцем."""
    assert message.from_user is not None
    telegram_id = message.from_user.id

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == user.id).order_by(Pet.id)
        )
        pets = list(pets_result.scalars().all())

        if not pets:
            text = (
                "У вас пока нет питомцев.\n\n"
                "Нажмите «➕ Добавить питомца», чтобы создать первую карту."
            )
        else:
            active_name = None
            if user.active_pet_id:
                for pet in pets:
                    if pet.id == user.active_pet_id:
                        active_name = pet.name
                        break

            if active_name:
                active_line = f"⭐ Активный: {active_name}"
            else:
                active_line = "Активный питомец не выбран."

            text = (
                f"{active_line}\n\n"
                "Список питомцев ниже. Нажмите на питомца, чтобы открыть карточку."
            )

        items: list[tuple[int, str]] = []
        for pet in pets:
            if pet.species == "cat":
                icon = "🐱"
            elif pet.species == "dog":
                icon = "🐶"
            else:
                icon = "🐾"
            prefix = "⭐ " if user.active_pet_id == pet.id else ""
            title = f"{prefix}{icon} {pet.name}"
            items.append((pet.id, title))

        kb = pets_list_kb(items)

    await message.answer(text, reply_markup=kb)


async def start_entry_flow(message: Message, state: FSMContext) -> None:
    """Запускает мастер добавления записи для активного питомца."""
    assert message.from_user is not None
    telegram_id = message.from_user.id

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        if not user.active_pet_id:
            await message.answer(
                "Сначала выберите активного питомца в разделе «Питомцы».",
                reply_markup=main_menu_kb(),
            )
            await show_pets_menu(message)
            return

    await state.set_state(AddEntryStates.type)
    await message.answer(
        "Выберите тип записи:",
        reply_markup=entry_type_kb(),
    )


async def handle_main_menu(message: Message, state: FSMContext) -> None:
    text = message.text or ""

    if text == MAIN_MENU_BUTTON_PETS:
        await show_pets_menu(message)
    elif text == MAIN_MENU_BUTTON_ENTRY:
        await start_entry_flow(message, state)
    elif text == MAIN_MENU_BUTTON_HISTORY:
        await show_history(message)
    elif text == MAIN_MENU_BUTTON_SUMMARY:
        await show_summary_menu(message)
    elif text == MAIN_MENU_BUTTON_SETTINGS:
        await message.answer("Раздел «Настройки» в разработке.", reply_markup=main_menu_kb())
    else:
        await message.answer(
            "Я не понял это сообщение. Пожалуйста, используйте кнопки меню внизу "
            "или команду /help.",
            reply_markup=main_menu_kb(),
        )


async def pets_back_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Возвращаю вас в главное меню. Выберите раздел внизу.",
        reply_markup=None,
    )
    await callback.answer()


async def pets_list_callback(callback: CallbackQuery) -> None:
    """Перерисовать список питомцев (из карточки назад к списку)."""
    assert callback.from_user is not None
    telegram_id = callback.from_user.id

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        pets_result = await session.execute(
            select(Pet).where(Pet.user_id == user.id).order_by(Pet.id)
        )
        pets = list(pets_result.scalars().all())

        if not pets:
            text = (
                "У вас пока нет питомцев.\n\n"
                "Нажмите «➕ Добавить питомца», чтобы создать первую карту."
            )
        else:
            active_name = None
            if user.active_pet_id:
                for pet in pets:
                    if pet.id == user.active_pet_id:
                        active_name = pet.name
                        break

            if active_name:
                active_line = f"⭐ Активный: {active_name}"
            else:
                active_line = "Активный питомец не выбран."

            text = (
                f"{active_line}\n\n"
                "Список питомцев ниже. Нажмите на питомца, чтобы открыть карточку."
            )

        items: list[tuple[int, str]] = []
        for pet in pets:
            if pet.species == "cat":
                icon = "🐱"
            elif pet.species == "dog":
                icon = "🐶"
            else:
                icon = "🐾"
            prefix = "⭐ " if user.active_pet_id == pet.id else ""
            title = f"{prefix}{icon} {pet.name}"
            items.append((pet.id, title))

        kb = pets_list_kb(items)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


async def pet_card_callback(callback: CallbackQuery) -> None:
    """Открыть карточку конкретного питомца по нажатию inline-кнопки."""
    assert callback.from_user is not None
    telegram_id = callback.from_user.id
    assert callback.data is not None

    _, _, raw_id = callback.data.partition(":")
    try:
        pet_id = int(raw_id)
    except ValueError:
        await callback.answer("Не удалось определить питомца", show_alert=True)
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            await callback.answer("Сначала используйте /start", show_alert=True)
            return

        pet_result = await session.execute(
            select(Pet).where(Pet.id == pet_id, Pet.user_id == user.id)
        )
        pet = pet_result.scalar_one_or_none()
        if pet is None:
            await callback.answer("Питомец не найден", show_alert=True)
            return

        species_map = {
            "cat": "Кот",
            "dog": "Пёс",
            "other": "Другое",
        }
        icon_map = {
            "cat": "🐱",
            "dog": "🐶",
        }
        species = species_map.get(pet.species, pet.species)
        species_icon = icon_map.get(pet.species, "🐾")
        age_line = "Возраст не указан."
        if pet.birth_date:
            # Грубый подсчёт возраста по годам
            years = max(0, datetime.utcnow().year - pet.birth_date.year)
            age_line = f"Возраст: ~{years} г."

        text = (
            f"{species_icon} <b>{pet.name}</b>\n"
            f"Вид: {species}\n"
            f"{age_line}"
        )
        kb = pet_card_kb(pet.id, is_active=(user.active_pet_id == pet.id))

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


async def pet_set_active_callback(callback: CallbackQuery) -> None:
    """Сделать питомца активным для пользователя."""
    assert callback.from_user is not None
    telegram_id = callback.from_user.id
    assert callback.data is not None

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return
    try:
        pet_id = int(parts[2])
    except ValueError:
        await callback.answer("Не удалось определить питомца", show_alert=True)
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            await callback.answer("Сначала используйте /start", show_alert=True)
            return

        pet_result = await session.execute(
            select(Pet).where(Pet.id == pet_id, Pet.user_id == user.id)
        )
        pet = pet_result.scalar_one_or_none()
        if pet is None:
            await callback.answer("Питомец не найден", show_alert=True)
            return

        user.active_pet_id = pet.id
        session.add(user)
        await session.commit()

        text = (
            f"🐾 <b>{pet.name}</b>\n"
            "Этот питомец теперь активен. Новые записи будут сохраняться для него."
        )
        kb = pet_card_kb(pet.id, is_active=True)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer("Сделан активным")


async def pets_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Старт мастера добавления питомца."""
    await state.set_state(AddPetStates.name)
    if callback.message:
        await callback.message.edit_text(
            "Введите имя питомца.\n\n"
            "В любой момент можно отправить /cancel для отмены.",
            reply_markup=None,
        )
    await callback.answer()


async def pets_add_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Имя не может быть пустым. Попробуйте ещё раз.")
        return

    await state.update_data(name=name)
    await state.set_state(AddPetStates.species)
    await message.answer(
        f"Имя: <b>{name}</b>\nВыберите вид питомца:",
        reply_markup=species_kb(),
    )


async def pets_add_species(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.data is not None
    _, _, species = callback.data.partition(":")
    if species not in {"cat", "dog", "other"}:
        await callback.answer("Выберите вид из списка", show_alert=True)
        return

    await state.update_data(species=species)
    await state.set_state(AddPetStates.breed)

    if callback.message:
        await callback.message.edit_text(
            "Введите породу питомца или нажмите «➡ Пропустить».",
            reply_markup=breed_skip_kb(),
        )
    await callback.answer()


async def pets_add_breed_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(breed=None)
    await finalize_pet_creation(callback, state)
    await callback.answer()


async def pets_add_breed(message: Message, state: FSMContext) -> None:
    breed = (message.text or "").strip()
    if not breed:
        await message.answer(
            "Порода не может быть пустой. Введите текст или нажмите «➡ Пропустить»."
        )
        return

    await state.update_data(breed=breed)
    await finalize_pet_creation(message, state)


async def finalize_pet_creation(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Создаёт питомца в БД на основе данных FSM."""
    data = await state.get_data()
    name = data.get("name")
    species = data.get("species")
    breed = data.get("breed")  # может быть None

    if not name or not species:
        # Что-то пошло не так, сбрасываем мастер
        await state.clear()
        if isinstance(event, Message):
            await event.answer(
                "Не удалось создать питомца. Попробуйте снова через раздел «Питомцы».",
                reply_markup=main_menu_kb(),
            )
        else:
            if event.message:
                await event.message.edit_text(
                    "Не удалось создать питомца. Попробуйте снова через раздел «Питомцы».",
                )
        return

    if isinstance(event, Message):
        assert event.from_user is not None
        telegram_id = event.from_user.id
    else:
        assert event.from_user is not None
        telegram_id = event.from_user.id

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        pet = Pet(
            user_id=user.id,
            name=name,
            species=species,
            breed=breed,
            birth_date=None,
        )
        session.add(pet)
        await session.commit()
        await session.refresh(pet)

    await state.clear()

    text = (
        f"Питомец <b>{pet.name}</b> создан.\n\n"
        "Вы можете сделать его активным, чтобы добавлять записи именно для него."
    )
    kb = pet_card_kb(pet.id, is_active=False)

    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        if event.message:
            await event.message.edit_text(text, reply_markup=kb)


async def entry_type_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор типа записи."""
    assert callback.data is not None
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return
    entry_type = parts[2]
    if entry_type not in {"symptom", "visit", "vaccine", "meds", "other"}:
        await callback.answer("Некорректный тип записи", show_alert=True)
        return

    await state.update_data(entry_type=entry_type)
    await state.set_state(AddEntryStates.date_choice)

    if callback.message:
        await callback.message.edit_text(
            "Выберите дату записи:",
            reply_markup=entry_date_kb(),
        )
    await callback.answer()


async def entry_date_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора сегодняшней/вчерашней даты или запроса ввода."""
    assert callback.data is not None
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return
    choice = parts[2]

    now = datetime.utcnow()
    if choice == "today":
        chosen_date = datetime(now.year, now.month, now.day)
        await state.update_data(date=chosen_date.isoformat())
        await state.set_state(AddEntryStates.text)
        if callback.message:
            await callback.message.edit_text(
                "Введите текст записи (описание симптома, визита и т.п.):"
            )
        await callback.answer()
    elif choice == "yesterday":
        y = now - timedelta(days=1)
        chosen_date = datetime(y.year, y.month, y.day)
        await state.update_data(date=chosen_date.isoformat())
        await state.set_state(AddEntryStates.text)
        if callback.message:
            await callback.message.edit_text(
                "Введите текст записи (описание симптома, визита и т.п.):"
            )
        await callback.answer()
    elif choice == "custom":
        await state.set_state(AddEntryStates.custom_date)
        if callback.message:
            await callback.message.edit_text(
                "Введите дату в формате YYYY-MM-DD:"
            )
        await callback.answer()
    else:
        await callback.answer("Некорректный выбор даты", show_alert=True)


async def entry_custom_date_message(message: Message, state: FSMContext) -> None:
    """Парсинг введённой пользователем даты."""
    text = (message.text or "").strip()
    try:
        dt = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        await message.answer(
            "Не удалось распознать дату. Введите в формате YYYY-MM-DD, например 2025-12-01."
        )
        return

    chosen_date = datetime(dt.year, dt.month, dt.day)
    await state.update_data(date=chosen_date.isoformat())
    await state.set_state(AddEntryStates.text)
    await message.answer("Введите текст записи (описание симптома, визита и т.п.):")


async def entry_text_message(message: Message, state: FSMContext) -> None:
    """Финальный шаг мастера: сохраняем запись в БД."""
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст записи не может быть пустым. Введите описание.")
        return

    data = await state.get_data()
    entry_type = data.get("entry_type")
    raw_date = data.get("date")

    if not entry_type or not raw_date:
        await state.clear()
        await message.answer(
            "Что-то пошло не так при сохранении записи. Попробуйте ещё раз.",
            reply_markup=main_menu_kb(),
        )
        return

    try:
        date = datetime.fromisoformat(raw_date)
    except ValueError:
        await state.clear()
        await message.answer(
            "Дата записи повреждена. Попробуйте создать запись заново.",
            reply_markup=main_menu_kb(),
        )
        return

    assert message.from_user is not None
    telegram_id = message.from_user.id

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        if not user.active_pet_id:
            await state.clear()
            await message.answer(
                "Активный питомец не выбран. Сначала выберите питомца в разделе «Питомцы».",
                reply_markup=main_menu_kb(),
            )
            return

        pet_result = await session.execute(
            select(Pet).where(Pet.id == user.active_pet_id)
        )
        pet = pet_result.scalar_one_or_none()
        if pet is None:
            await state.clear()
            await message.answer(
                "Активный питомец не найден. Попробуйте выбрать его заново.",
                reply_markup=main_menu_kb(),
            )
            return

        entry = Entry(
            pet_id=pet.id,
            type=entry_type,
            date=date,
            text=text,
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)

    await state.clear()

    type_names = {
        "symptom": "Симптом",
        "visit": "Визит",
        "vaccine": "Прививка",
        "meds": "Лекарство",
        "other": "Другое",
    }
    type_title = type_names.get(entry_type, entry_type)
    date_str = date.strftime("%Y-%m-%d")

    builder = InlineKeyboardBuilder()
    builder.button(
        text="📎 Прикрепить файлы",
        callback_data=f"entry:attach:{entry.id}",
    )
    if entry_type == "vaccine":
        builder.button(
            text="⏰ Напомнить о следующей прививке",
            callback_data=f"vrem:start:{entry.id}",
        )
    elif entry_type == "meds":
        builder.button(
            text="💊 Это глистогонное: напомнить повтор через 10 дней",
            callback_data=f"mrem:start:{entry.id}",
        )
    builder.adjust(1)

    await message.answer(
        f"Запись сохранена ✅\n\n"
        f"Питомец: <b>{pet.name}</b>\n"
        f"Тип: {type_title}\n"
        f"Дата: {date_str}\n\n"
        "Вы можете прикрепить к этой записи файлы (фото, документы) сейчас "
        "или сделать это позже через историю.",
        reply_markup=builder.as_markup(),
    )


def build_vaccine_keyboard(species: str) -> InlineKeyboardBuilder:
    """Возвращает клавиатуру с типовыми прививками для кошек/собак."""
    builder = InlineKeyboardBuilder()
    if species == "dog":
        builder.button(
            text="Бешенство", callback_data="vrem:vaccine:rabies"
        )
        builder.button(
            text="Комплекс DHPPi", callback_data="vrem:vaccine:dhppi"
        )
        builder.button(
            text="Лептоспироз", callback_data="vrem:vaccine:lepto"
        )
    elif species == "cat":
        builder.button(
            text="Бешенство", callback_data="vrem:vaccine:rabies"
        )
        builder.button(
            text="Панлейкопения/ринотрахеит/калицивирус",
            callback_data="vrem:vaccine:pcr",
        )
    builder.button(
        text="Другая прививка", callback_data="vrem:vaccine:other"
    )
    builder.adjust(1)
    return builder


def build_delay_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="Через 1 месяц", callback_data="vrem:delay:30")
    builder.button(text="Через 3 месяца", callback_data="vrem:delay:90")
    builder.button(text="Через 6 месяцев", callback_data="vrem:delay:180")
    builder.button(text="Через 1 год", callback_data="vrem:delay:365")
    builder.button(text="Ввести дни", callback_data="vrem:delay:custom")
    builder.adjust(1)
    return builder


async def vaccine_reminder_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Старт мастера напоминания о прививке для конкретной записи."""
    assert callback.data is not None
    assert callback.from_user is not None
    telegram_id = callback.from_user.id

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return
    try:
        entry_id = int(parts[2])
    except ValueError:
        await callback.answer("Не удалось определить запись", show_alert=True)
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Сначала используйте /start", show_alert=True)
            return

        entry_result = await session.execute(
            select(Entry)
            .join(Pet, Entry.pet_id == Pet.id)
            .where(Entry.id == entry_id, Pet.user_id == user.id)
        )
        entry = entry_result.scalar_one_or_none()
        if not entry:
            await callback.answer("Запись не найдена", show_alert=True)
            return

        pet_result = await session.execute(
            select(Pet).where(Pet.id == entry.pet_id)
        )
        pet = pet_result.scalar_one_or_none()

    if not pet:
        await callback.answer("Питомец не найден", show_alert=True)
        return

    await state.set_state(VaccineReminderStates.choosing_vaccine)
    await state.update_data(
        entry_id=entry_id,
        pet_id=pet.id,
        pet_name=pet.name,
        species=pet.species,
    )

    kb = build_vaccine_keyboard(pet.species)

    if callback.message:
        await callback.message.edit_text(
            f"Для питомца <b>{pet.name}</b> выберите тип прививки:",
            reply_markup=kb.as_markup(),
        )
    await callback.answer()


async def vaccine_choose_vaccine(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор конкретной прививки для напоминания."""
    assert callback.data is not None

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    slug = parts[2]
    title_map = {
        "rabies": "Прививка от бешенства",
        "dhppi": "Комплекс DHPPi",
        "lepto": "Прививка от лептоспироза",
        "pcr": "Комплекс ПКР (панлейкопения/ринотрахеит/калицивирус)",
        "other": "Прививка (другая)",
    }
    title = title_map.get(slug, "Прививка")

    await state.update_data(reminder_title=title)
    await state.set_state(VaccineReminderStates.choosing_delay)

    kb = build_delay_keyboard()
    if callback.message:
        await callback.message.edit_text(
            f"{title}\n\n"
            "Через сколько времени напомнить о следующей прививке?",
            reply_markup=kb.as_markup(),
        )
    await callback.answer()


async def vaccine_choose_delay(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор фиксированного интервала или запроса ввода дней."""
    assert callback.data is not None

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    value = parts[2]
    if value == "custom":
        await state.set_state(VaccineReminderStates.custom_delay)
        if callback.message:
            await callback.message.edit_text(
                "Введите через сколько дней напомнить (целое число):"
            )
        await callback.answer()
        return

    try:
        days = int(value)
    except ValueError:
        await callback.answer("Некорректное значение", show_alert=True)
        return

    await _create_vaccine_reminder(callback, state, days)


async def vaccine_custom_delay_message(message: Message, state: FSMContext) -> None:
    """Парсинг введённого пользователем количества дней до напоминания."""
    text = (message.text or "").strip()
    try:
        days = int(text)
    except ValueError:
        await message.answer("Нужно ввести целое число дней, например 30.")
        return

    if days <= 0:
        await message.answer("Число дней должно быть больше нуля.")
        return

    await _create_vaccine_reminder(message, state, days)


async def _create_vaccine_reminder(
    event: Message | CallbackQuery,
    state: FSMContext,
    days: int,
) -> None:
    """Фактическое создание напоминания в БД."""
    data = await state.get_data()
    entry_id = data.get("entry_id")
    pet_id = data.get("pet_id")
    pet_name = data.get("pet_name")
    title = data.get("reminder_title", "Прививка")

    if isinstance(event, Message):
        assert event.from_user is not None
        telegram_id = event.from_user.id
    else:
        assert event.from_user is not None
        telegram_id = event.from_user.id

    due_at = datetime.utcnow() + timedelta(days=days)

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        reminder = Reminder(
            user_id=user.id,
            pet_id=pet_id,
            entry_id=entry_id,
            title=title,
            due_at=due_at,
            period_days=None,
            is_done=False,
        )
        session.add(reminder)
        await session.commit()

    await state.clear()

    due_str = due_at.strftime("%Y-%m-%d")
    text = (
        f"Напоминание создано ✅\n\n"
        f"Питомец: <b>{pet_name}</b>\n"
        f"Событие: {title}\n"
        f"Дата напоминания: {due_str}"
    )

    if isinstance(event, Message):
        await event.answer(text, reply_markup=main_menu_kb())
    else:
        if event.message:
            await event.message.edit_text(text, reply_markup=None)
        await event.answer()


async def meds_dewormer_reminder_start(callback: CallbackQuery) -> None:
    """Создаёт напоминание о повторной даче глистогонного через 10 дней."""
    assert callback.data is not None
    assert callback.from_user is not None
    telegram_id = callback.from_user.id

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    try:
        entry_id = int(parts[2])
    except ValueError:
        await callback.answer("Не удалось определить запись", show_alert=True)
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Сначала используйте /start", show_alert=True)
            return

        entry_result = await session.execute(
            select(Entry)
            .join(Pet, Entry.pet_id == Pet.id)
            .where(Entry.id == entry_id, Pet.user_id == user.id)
        )
        entry = entry_result.scalar_one_or_none()
        if not entry:
            await callback.answer("Запись не найдена", show_alert=True)
            return

        pet_result = await session.execute(
            select(Pet).where(Pet.id == entry.pet_id)
        )
        pet = pet_result.scalar_one_or_none()
        if not pet:
            await callback.answer("Питомец не найден", show_alert=True)
            return

        # повтор через 10 дней от даты приёма лекарства
        due_at = entry.date + timedelta(days=10)

        reminder = Reminder(
            user_id=user.id,
            pet_id=pet.id,
            entry_id=entry.id,
            title="Повтор глистогонного",
            due_at=due_at,
            period_days=None,
            is_done=False,
        )
        session.add(reminder)
        await session.commit()

    due_str = due_at.strftime("%Y-%m-%d")
    if callback.message:
        await callback.message.edit_text(
            f"Напоминание о повторной даче глистогонного создано ✅\n\n"
            f"Питомец: <b>{pet.name}</b>\n"
            f"Дата напоминания: {due_str}",
        )
    await callback.answer()


async def entry_attach_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало сценария прикрепления файлов к записи."""
    assert callback.data is not None
    assert callback.from_user is not None
    telegram_id = callback.from_user.id

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    try:
        entry_id = int(parts[2])
    except ValueError:
        await callback.answer("Не удалось определить запись", show_alert=True)
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Сначала используйте /start", show_alert=True)
            return

        entry_result = await session.execute(
            select(Entry)
            .join(Pet, Entry.pet_id == Pet.id)
            .where(Entry.id == entry_id, Pet.user_id == user.id)
        )
        entry = entry_result.scalar_one_or_none()
        if not entry:
            await callback.answer("Запись не найдена", show_alert=True)
            return

    await state.set_state(AttachFilesStates.adding)
    await state.update_data(entry_id=entry_id)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Готово", callback_data="entry:attach_done")
    builder.adjust(1)

    if callback.message:
        await callback.message.edit_text(
            "Отправьте фото и/или документы, которые нужно прикрепить к записи.\n\n"
            "Когда закончите — нажмите «✅ Готово» или отправьте /cancel для отмены.",
            reply_markup=builder.as_markup(),
        )
    await callback.answer()


async def entry_attach_photo(message: Message, state: FSMContext) -> None:
    """Приём фото во время сценария прикрепления файлов."""
    data = await state.get_data()
    entry_id = data.get("entry_id")
    if not entry_id or not message.photo:
        return

    photo = message.photo[-1]

    async with get_session() as session:
        attachment = Attachment(
            entry_id=entry_id,
            kind="photo",
            file_id=photo.file_id,
            file_unique_id=getattr(photo, "file_unique_id", None),
        )
        session.add(attachment)
        await session.commit()

    await message.answer("Фото прикреплено ✅")


async def entry_attach_document(message: Message, state: FSMContext) -> None:
    """Приём документа во время сценария прикрепления файлов."""
    data = await state.get_data()
    entry_id = data.get("entry_id")
    if not entry_id or not message.document:
        return

    doc = message.document

    async with get_session() as session:
        attachment = Attachment(
            entry_id=entry_id,
            kind="document",
            file_id=doc.file_id,
            file_unique_id=getattr(doc, "file_unique_id", None),
        )
        session.add(attachment)
        await session.commit()

    await message.answer("Документ прикреплён ✅")


async def entry_attach_done(callback: CallbackQuery, state: FSMContext) -> None:
    """Завершение сценария прикрепления файлов."""
    await state.clear()
    if callback.message:
        await callback.message.edit_text(
            "Прикрепление файлов завершено. Вы всегда можете посмотреть их через историю.",
        )
    await callback.answer()


async def show_history(message: Message) -> None:
    """Показывает последние 10 записей активного питомца (без фильтров)."""
    assert message.from_user is not None
    telegram_id = message.from_user.id

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        if not user.active_pet_id:
            await message.answer(
                "Активный питомец не выбран. Откройте раздел «Питомцы» и сделайте питомца активным.",
                reply_markup=main_menu_kb(),
            )
            return

        pet_result = await session.execute(
            select(Pet).where(Pet.id == user.active_pet_id)
        )
        pet = pet_result.scalar_one_or_none()
        if pet is None:
            await message.answer(
                "Активный питомец не найден. Попробуйте выбрать его заново.",
                reply_markup=main_menu_kb(),
            )
            return

        entries_result = await session.execute(
            select(Entry)
            .where(Entry.pet_id == pet.id)
            .order_by(Entry.date.desc())
            .limit(10)
        )
        entries = list(entries_result.scalars().all())

    if not entries:
        await message.answer(
            f"Для питомца <b>{pet.name}</b> пока нет записей.",
            reply_markup=main_menu_kb(),
        )
        return

    type_names = {
        "symptom": "🤒 Симптом",
        "visit": "🏥 Визит",
        "vaccine": "💉 Прививка",
        "meds": "💊 Лекарство",
        "other": "📝 Другое",
    }

    builder = InlineKeyboardBuilder()
    for e in entries:
        date_str = e.date.strftime("%Y-%m-%d")
        type_title = type_names.get(e.type, e.type)
        text_preview = e.text.strip().replace("\n", " ")
        if len(text_preview) > 40:
            text_preview = text_preview[:37] + "..."
        button_text = f"{date_str} · {type_title}: {text_preview}"
        builder.button(text=button_text, callback_data=f"entry:view:{e.id}")
    builder.adjust(1)

    await message.answer(
        f"Последние записи для питомца <b>{pet.name}</b>:\n\n"
        "Нажмите на запись, чтобы посмотреть детали и файлы.",
        reply_markup=builder.as_markup(),
    )


async def entry_view_callback(callback: CallbackQuery) -> None:
    """Открывает карточку записи с краткой информацией и доступом к файлам."""
    assert callback.data is not None
    assert callback.from_user is not None
    telegram_id = callback.from_user.id

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    try:
        entry_id = int(parts[2])
    except ValueError:
        await callback.answer("Не удалось определить запись", show_alert=True)
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Сначала используйте /start", show_alert=True)
            return

        entry_result = await session.execute(
            select(Entry)
            .join(Pet, Entry.pet_id == Pet.id)
            .where(Entry.id == entry_id, Pet.user_id == user.id)
        )
        entry = entry_result.scalar_one_or_none()
        if not entry:
            await callback.answer("Запись не найдена", show_alert=True)
            return

        # подгружаем количество файлов
        attachments_result = await session.execute(
            select(Attachment).where(Attachment.entry_id == entry.id)
        )
        attachments = list(attachments_result.scalars().all())

    type_names = {
        "symptom": "🤒 Симптом",
        "visit": "🏥 Визит",
        "vaccine": "💉 Прививка",
        "meds": "💊 Лекарство",
        "other": "📝 Другое",
    }
    type_title = type_names.get(entry.type, entry.type)
    date_str = entry.date.strftime("%Y-%m-%d")
    files_count = len(attachments)

    text = (
        f"Дата: {date_str}\n"
        f"Тип: {type_title}\n"
        f"Файлов: {files_count}\n\n"
        f"{entry.text}"
    )

    builder = InlineKeyboardBuilder()
    if files_count:
        builder.button(
            text=f"📎 Файлы ({files_count})",
            callback_data=f"entry:files:{entry.id}",
        )
    builder.button(text="⬅ К истории", callback_data="history:back")
    builder.adjust(1)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


async def entry_files_callback(callback: CallbackQuery) -> None:
    """Показывает список файлов записи и даёт возможность переслать каждый по клику."""
    assert callback.data is not None
    assert callback.from_user is not None
    telegram_id = callback.from_user.id

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    try:
        entry_id = int(parts[2])
    except ValueError:
        await callback.answer("Не удалось определить запись", show_alert=True)
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Сначала используйте /start", show_alert=True)
            return

        attachments_result = await session.execute(
            select(Attachment)
            .join(Entry, Attachment.entry_id == Entry.id)
            .join(Pet, Entry.pet_id == Pet.id)
            .where(Attachment.entry_id == entry_id, Pet.user_id == user.id)
        )
        attachments = list(attachments_result.scalars().all())

    if not attachments:
        await callback.answer("У этой записи пока нет файлов", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for idx, att in enumerate(attachments, start=1):
        if att.kind == "photo":
            title = f"🖼 Фото {idx}"
        else:
            title = f"📄 Документ {idx}"
        builder.button(
            text=title,
            callback_data=f"file:send:{att.id}",
        )
    builder.adjust(1)

    if callback.message:
        await callback.message.edit_text(
            "Файлы этой записи:",
            reply_markup=builder.as_markup(),
        )
    await callback.answer()


async def file_send_callback(callback: CallbackQuery) -> None:
    """Переотправка выбранного файла по file_id."""
    assert callback.data is not None
    assert callback.from_user is not None
    telegram_id = callback.from_user.id

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    try:
        attachment_id = int(parts[2])
    except ValueError:
        await callback.answer("Не удалось определить файл", show_alert=True)
        return

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Сначала используйте /start", show_alert=True)
            return

        attachment_result = await session.execute(
            select(Attachment)
            .join(Entry, Attachment.entry_id == Entry.id)
            .join(Pet, Entry.pet_id == Pet.id)
            .where(Attachment.id == attachment_id, Pet.user_id == user.id)
        )
        attachment = attachment_result.scalar_one_or_none()
        if not attachment:
            await callback.answer("Файл не найден", show_alert=True)
            return

    if not callback.message:
        await callback.answer()
        return

    if attachment.kind == "photo":
        await callback.message.answer_photo(attachment.file_id)
    else:
        await callback.message.answer_document(attachment.file_id)

    await callback.answer()


async def history_back_callback(callback: CallbackQuery) -> None:
    """Возврат к списку истории из карточки записи."""
    if callback.message:
        await show_history(callback.message)
    await callback.answer()


async def show_summary_menu(message: Message) -> None:
    """Показывает выбор периода сводки."""
    await message.answer(
        "Выберите период для сводки:",
        reply_markup=summary_periods_kb(),
    )


async def summary_period_callback(callback: CallbackQuery) -> None:
    """Формирует и отправляет текстовую сводку за выбранный период для активного питомца."""
    assert callback.from_user is not None
    telegram_id = callback.from_user.id
    assert callback.data is not None

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    try:
        days = int(parts[2])
    except ValueError:
        await callback.answer("Некорректный период", show_alert=True)
        return

    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        if not user.active_pet_id:
            if callback.message:
                await callback.message.edit_text(
                    "Активный питомец не выбран. Откройте раздел «Питомцы» и сделайте питомца активным.",
                )
            await callback.answer()
            return

        pet_result = await session.execute(
            select(Pet).where(Pet.id == user.active_pet_id)
        )
        pet = pet_result.scalar_one_or_none()
        if pet is None:
            if callback.message:
                await callback.message.edit_text(
                    "Активный питомец не найден. Попробуйте выбрать его заново.",
                )
            await callback.answer()
            return

        entries_result = await session.execute(
            select(Entry)
            .where(
                Entry.pet_id == pet.id,
                Entry.date >= start_date,
                Entry.date <= now,
            )
            .order_by(Entry.date.asc())
        )
        entries = list(entries_result.scalars().all())

    if not entries:
        text = (
            f"За последние {days} дн. для питомца <b>{pet.name}</b> записей нет."
        )
    else:
        type_names = {
            "symptom": "🤒 Симптом",
            "visit": "🏥 Визит",
            "vaccine": "💉 Прививка",
            "meds": "💊 Лекарство",
            "other": "📝 Другое",
        }
        lines: list[str] = []
        for e in entries:
            date_str = e.date.strftime("%Y-%m-%d")
            type_title = type_names.get(e.type, e.type)
            lines.append(f"{date_str} · {type_title}: {e.text}")

        body = "\n".join(lines)
        date_from_str = start_date.strftime("%Y-%m-%d")
        date_to_str = now.strftime("%Y-%m-%d")
        text = (
            f"Сводка для питомца <b>{pet.name}</b>\n"
            f"Период: {date_from_str} — {date_to_str}\n\n"
            f"{body}"
        )

    if callback.message:
        await callback.message.edit_text(text)
    await callback.answer()



def setup_routes(dp: Dispatcher) -> None:
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command(commands={"help"}))
    dp.message.register(cmd_cancel, Command(commands={"cancel"}))

    # FSM добавления питомца
    dp.message.register(pets_add_name, AddPetStates.name)
    dp.callback_query.register(
        pets_add_species,
        F.data.startswith("species:"),
        AddPetStates.species,
    )
    dp.callback_query.register(
        pets_add_breed_skip,
        F.data == "breed:skip",
        AddPetStates.breed,
    )
    dp.message.register(pets_add_breed, AddPetStates.breed)

    # FSM добавления записи
    dp.callback_query.register(
        entry_type_callback,
        F.data.startswith("entry:type:"),
        AddEntryStates.type,
    )
    dp.callback_query.register(
        entry_date_callback,
        F.data.startswith("entry:date:"),
        AddEntryStates.date_choice,
    )
    dp.message.register(
        entry_custom_date_message,
        AddEntryStates.custom_date,
    )
    dp.message.register(
        entry_text_message,
        AddEntryStates.text,
    )

    # Напоминания о прививках
    dp.callback_query.register(
        vaccine_reminder_start,
        F.data.startswith("vrem:start:"),
    )
    dp.callback_query.register(
        vaccine_choose_vaccine,
        F.data.startswith("vrem:vaccine:"),
        VaccineReminderStates.choosing_vaccine,
    )
    dp.callback_query.register(
        vaccine_choose_delay,
        F.data.startswith("vrem:delay:"),
        VaccineReminderStates.choosing_delay,
    )
    dp.message.register(
        vaccine_custom_delay_message,
        VaccineReminderStates.custom_delay,
    )

    dp.callback_query.register(
        meds_dewormer_reminder_start,
        F.data.startswith("mrem:start:"),
    )

    # Прикрепление файлов к записи
    dp.callback_query.register(
        entry_attach_start,
        F.data.startswith("entry:attach:"),
    )
    dp.callback_query.register(
        entry_attach_done,
        F.data == "entry:attach_done",
        AttachFilesStates.adding,
    )
    dp.message.register(
        entry_attach_photo,
        AttachFilesStates.adding,
        F.photo,
    )
    dp.message.register(
        entry_attach_document,
        AttachFilesStates.adding,
        F.document,
    )

    # Callback-и раздела «Питомцы»
    dp.callback_query.register(
        pets_add_start,
        F.data == "pets:add",
    )
    dp.callback_query.register(
        pets_back_callback,
        F.data == "pets:back",
    )
    dp.callback_query.register(
        pets_list_callback,
        F.data == "pets:list",
    )
    dp.callback_query.register(
        pet_set_active_callback,
        F.data.startswith("pet:set_active:"),
    )
    dp.callback_query.register(
        pet_card_callback,
        F.data.startswith("pet:"),
    )

    # Callback-и истории и файлов
    dp.callback_query.register(
        entry_view_callback,
        F.data.startswith("entry:view:"),
    )
    dp.callback_query.register(
        entry_files_callback,
        F.data.startswith("entry:files:"),
    )
    dp.callback_query.register(
        file_send_callback,
        F.data.startswith("file:send:"),
    )
    dp.callback_query.register(
        history_back_callback,
        F.data == "history:back",
    )

    # Callback-и для сводки
    dp.callback_query.register(
        summary_period_callback,
        F.data.startswith("summary:days:"),
    )

    # Обработка нажатий на текстовые кнопки главного меню
    dp.message.register(
        handle_main_menu,
        F.text.in_(
            {
                MAIN_MENU_BUTTON_PETS,
                MAIN_MENU_BUTTON_ENTRY,
                MAIN_MENU_BUTTON_HISTORY,
                MAIN_MENU_BUTTON_SUMMARY,
                MAIN_MENU_BUTTON_SETTINGS,
            }
        ),
    )

    # Фолбэк — всё остальное
    dp.message.register(handle_main_menu)


async def main() -> None:
    settings = load_settings()
    await init_db()

    bot = Bot(
        settings.bot.token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()
    setup_routes(dp)

    async def reminders_worker() -> None:
        """Периодически проверяет напоминания и отправляет их пользователям."""
        while True:
            now = datetime.utcnow()
            async with get_session() as session:
                result = await session.execute(
                    select(Reminder, Pet, User)
                    .join(Pet, Reminder.pet_id == Pet.id)
                    .join(User, Reminder.user_id == User.id)
                    .where(
                        Reminder.is_done.is_(False),
                        Reminder.due_at <= now,
                    )
                )
                rows = result.all()

                for reminder, pet, user in rows:
                    try:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=(
                                f"⏰ Напоминание о прививке\n\n"
                                f"Питомец: <b>{pet.name}</b>\n"
                                f"Событие: {reminder.title}\n"
                                f"Дата: {reminder.due_at.strftime('%Y-%m-%d')}"
                            ),
                        )
                    except Exception:
                        # В MVP просто помечаем как выполненное даже при ошибке отправки
                        pass

                    reminder.is_done = True
                    reminder.last_sent_at = now
                    session.add(reminder)

                await session.commit()

            await asyncio.sleep(60)

    # запускаем воркер напоминаний параллельно с polling
    asyncio.create_task(reminders_worker())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    with suppress(KeyboardInterrupt, SystemExit):
        asyncio.run(main())


