from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class BotConfig:
    token: str


@dataclass
class DatabaseConfig:
    url: str


@dataclass
class Settings:
    bot: BotConfig
    db: DatabaseConfig


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set in environment or .env file")

    db_url = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")

    return Settings(
        bot=BotConfig(token=token),
        db=DatabaseConfig(url=db_url),
    )




