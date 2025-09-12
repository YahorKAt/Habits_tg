from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .models import RepeatType


class TaskCreate(BaseModel):
    title: str
    repeat_type: RepeatType = RepeatType.NONE
    repeat_interval: int = 1
    next_due_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category: str = 'general'


class SubtaskCreate(BaseModel):
    task_id: int
    title: str


class SubtaskOut(BaseModel):
    id: int
    task_id: int
    title: str
    created_at: datetime
    completed: bool

    class Config:
        orm_mode = True


class TaskOut(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    completed: bool
    repeat_type: RepeatType
    repeat_interval: int
    next_due_date: Optional[datetime]
    end_date: Optional[datetime]
    last_completed_date: Optional[datetime]
    category: str
    subtasks: List[SubtaskOut] = []

    class Config:
        orm_mode = True


class StatsOut(BaseModel):
    period: str
    tasks_completed: int
    subtasks_completed: int
    total_completed: int


class NoteCreate(BaseModel):
    content: str
    date: str  # YYYY-MM-DD


class NoteOut(BaseModel):
    id: int
    user_id: int
    content: str
    date: str
    created_at: datetime

    class Config:
        orm_mode = True




