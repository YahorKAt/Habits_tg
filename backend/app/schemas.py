from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from .models import RepeatType


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    repeat_type: RepeatType = RepeatType.NONE
    repeat_interval: int = 1
    next_due_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category: str = 'personal'
    frequency: str = 'daily'


class SubtaskCreate(BaseModel):
    task_id: int
    title: str


class SubtaskOut(BaseModel):
    id: int
    task_id: int
    title: str
    created_at: datetime
    completed: bool

    model_config = ConfigDict(from_attributes=True)


class TaskOut(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    created_at: datetime
    completed: bool
    repeat_type: RepeatType
    repeat_interval: int
    next_due_date: Optional[datetime]
    end_date: Optional[datetime]
    last_completed_date: Optional[datetime]
    category: str
    frequency: str
    subtasks: List[SubtaskOut] = []

    model_config = ConfigDict(from_attributes=True)


class StatsOut(BaseModel):
    period: str
    tasks_completed: int
    subtasks_completed: int
    total_completed: int


class NoteCreate(BaseModel):
    content: str
    date: str  # YYYY-MM-DD
    mood: Optional[str] = None  # Эмоджи настроения


class NoteOut(BaseModel):
    id: int
    user_id: int
    content: str
    date: str
    mood: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




