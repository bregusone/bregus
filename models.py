from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    active_pet_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pets.id"), nullable=True
    )


class Pet(Base):
    __tablename__ = "pets"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    species: Mapped[str] = mapped_column(String(32))
    breed: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    birth_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    entries: Mapped[list["Entry"]] = relationship(
        back_populates="pet", cascade="all, delete-orphan"
    )


class Entry(Base):
    __tablename__ = "entries"

    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"), index=True)
    type: Mapped[str] = mapped_column(String(16))  # symptom/visit/vaccine/meds/other
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    text: Mapped[str] = mapped_column(Text)

    pet: Mapped[Pet] = relationship(back_populates="entries")
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachments"

    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # photo/document
    file_id: Mapped[str] = mapped_column(String(256))
    file_unique_id: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, unique=True
    )

    entry: Mapped[Entry] = relationship(back_populates="attachments")




