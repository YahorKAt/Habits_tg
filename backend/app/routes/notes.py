"""
Роутеры для работы с заметками
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_user_id
from ..schemas import NoteCreate
from ..repositories.note_repository import NoteRepository

router = APIRouter()


@router.post("/notes")
def add_note(
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Создает новую заметку"""
    note = NoteRepository.create(
        db,
        user_id=user_id,
        content=payload.content,
        date=payload.date,
        mood=payload.mood
    )
    return note


@router.put("/notes/{note_id}")
def update_note(
    note_id: int,
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Обновляет заметку"""
    note = NoteRepository.update(
        db,
        note_id=note_id,
        user_id=user_id,
        content=payload.content,
        date=payload.date,
        mood=payload.mood
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.get("/notes")
def list_notes(
    date: str = None,
    year: int = None,
    month: int = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Получает заметки"""
    # Если указан год и месяц - возвращаем все заметки за месяц
    if year is not None and month is not None:
        notes_dict = NoteRepository.get_by_month(db, user_id=user_id, year=year, month=month)
        return list(notes_dict.values())
    
    # Иначе возвращаем заметки за конкретную дату
    if date:
        return NoteRepository.get_by_date(db, user_id=user_id, date=date)
    
    return []


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Удаляет заметку"""
    deleted = NoteRepository.delete(db, note_id=note_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}

