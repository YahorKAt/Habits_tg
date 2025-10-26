from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, func, Enum
from sqlalchemy.orm import relationship
from .database import Base
import enum


class RepeatType(enum.Enum):
    NONE = "NONE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    CUSTOM = "CUSTOM"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)  # Описание задачи
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed = Column(Boolean, default=False, nullable=False)
    
    # Новые поля для повторяющихся задач
    repeat_type = Column(Enum(RepeatType), default=RepeatType.NONE, nullable=False)
    repeat_interval = Column(Integer, default=1, nullable=False)  # каждые N дней/недель/месяцев
    next_due_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)  # когда прекратить повторение
    last_completed_date = Column(DateTime(timezone=True), nullable=True)
    
    # Поле для группы задачи
    category = Column(String(50), default='general', nullable=False)  # general, sport, study, work, etc.
    
    # Поле для частоты выполнения
    frequency = Column(String(20), default='daily', nullable=False)  # daily, weekly, monthly

    subtasks = relationship("Subtask", cascade="all, delete-orphan", back_populates="task")


class Subtask(Base):
    __tablename__ = "subtasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed = Column(Boolean, default=False, nullable=False)

    task = relationship("Task", back_populates="subtasks")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    content = Column(String(1000), nullable=False)  # Текст заметки
    date = Column(String(10), nullable=False)  # Дата в формате YYYY-MM-DD
    mood = Column(String(10), nullable=True)  # Эмоджи настроения
    created_at = Column(DateTime(timezone=True), server_default=func.now())




