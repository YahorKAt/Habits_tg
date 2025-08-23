from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TaskCreate(BaseModel):
    title: str


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
    subtasks: List[SubtaskOut] = []

    class Config:
        orm_mode = True


class StatsOut(BaseModel):
    period: str
    tasks_completed: int
    subtasks_completed: int
    total_completed: int




