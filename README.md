## Pet Health Diary Telegram Bot (MVP)

Telegram-бот для ведения истории здоровья питомцев:
- профиль питомца
- записи (симптомы, визиты, прививки, лекарства, другое)
- вложения (фото, документы)
- сводка за период

### Технологии
- Python 3.11+
- aiogram 3
- SQLite + SQLAlchemy (опционально Alembic для миграций)

### Быстрый старт (локально)

1. Создать и активировать виртуальное окружение (опционально):
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

2. Установить зависимости:
```bash
pip install -r requirements.txt
```

3. Создать файл `.env` в корне проекта:
```bash
BOT_TOKEN=ваш_токен_бота_из_BotFather
```

4. Запустить бота:
```bash
python -m app.bot
```






