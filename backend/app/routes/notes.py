"""
Роутеры для работы с заметками
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from ..dependencies import get_user_id
from ..schemas import NoteCreate
from ..repositories.note_repository import NoteRepository

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/notes")
def add_note(
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Создает новую заметку"""
    logger.info(f"📝 Получен запрос на создание заметки от пользователя {user_id} для даты {payload.date}")
    logger.debug(f"   Настроение: {payload.mood}, длина текста: {len(payload.content)} символов")
    note = NoteRepository.create(
        db,
        user_id=user_id,
        content=payload.content,
        date=payload.date,
        mood=payload.mood
    )
    logger.info(f"✅ Заметка {note.id} успешно создана для пользователя {user_id}")
    return note


@router.put("/notes/{note_id}")
def update_note(
    note_id: int,
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Обновляет заметку"""
    logger.info(f"✏️  Получен запрос на обновление заметки {note_id} от пользователя {user_id}")
    note = NoteRepository.update(
        db,
        note_id=note_id,
        user_id=user_id,
        content=payload.content,
        date=payload.date,
        mood=payload.mood
    )
    if not note:
        logger.warning(f"⚠️  Заметка {note_id} не найдена для обновления пользователем {user_id}")
        raise HTTPException(status_code=404, detail="Note not found")
    logger.info(f"✅ Заметка {note_id} успешно обновлена пользователем {user_id}")
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
        logger.info(f"📋 Получен запрос на заметки за месяц {year}-{month:02d} от пользователя {user_id}")
        notes_dict = NoteRepository.get_by_month(db, user_id=user_id, year=year, month=month)
        notes_list = list(notes_dict.values())
        logger.info(f"✅ Возвращено {len(notes_list)} заметок за месяц для пользователя {user_id}")
        return notes_list
    
    # Иначе возвращаем заметки за конкретную дату
    if date:
        logger.info(f"📋 Получен запрос на заметки за дату {date} от пользователя {user_id}")
        notes = NoteRepository.get_by_date(db, user_id=user_id, date=date)
        logger.info(f"✅ Возвращено {len(notes)} заметок за дату {date} для пользователя {user_id}")
        return notes
    
    logger.info(f"📋 Получен запрос на заметки без параметров от пользователя {user_id}")
    return []


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Удаляет заметку"""
    logger.info(f"🗑️  Получен запрос на удаление заметки {note_id} от пользователя {user_id}")
    deleted = NoteRepository.delete(db, note_id=note_id, user_id=user_id)
    if not deleted:
        logger.warning(f"⚠️  Заметка {note_id} не найдена для удаления пользователем {user_id}")
        raise HTTPException(status_code=404, detail="Note not found")
    logger.info(f"✅ Заметка {note_id} успешно удалена пользователем {user_id}")
    return {"ok": True}

