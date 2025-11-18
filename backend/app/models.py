from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship
from .database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed = Column(Boolean, default=False, nullable=False)
    
    # Поле для связи с оригинальной задачей (для повторяющихся задач)
    parent_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Поля для повторяющихся задач
    repeat_interval = Column(Integer, default=1, nullable=False)  # каждые N дней/недель/месяцев
    next_due_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)  # когда прекратить повторение
    last_completed_date = Column(DateTime(timezone=True), nullable=True)
    
    # Поле для группы задачи
    category = Column(String(50), default='general', nullable=False)  # general, sport, study, work, etc.

    # Поле для частоты выполнения
    frequency = Column(String(20), default='daily', nullable=False)  # daily, weekly, monthly
    
    # Поле для стрика (количество последовательных выполнений)
    streak = Column(Integer, default=0, nullable=False)
    
    # Поле для мягкого удаления (архивирование)
    deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)  # Telegram user_id
    timezone_offset = Column(String(10), nullable=True)  # Например: "+03:00" или "-05:00"
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())




