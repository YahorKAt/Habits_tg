"""
Репозиторий для работы с заметками
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, Dict
from datetime import date

from .. import models


class NoteRepository:
    """Репозиторий для работы с заметками"""
    
    @staticmethod
    def create(
        db: Session,
        user_id: int,
        content: str,
        date: str,
        mood: Optional[str] = None
    ) -> models.Note:
        """Создает новую заметку"""
        note = models.Note(
            user_id=user_id,
            content=content,
            date=date,
            mood=mood
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note
    
    @staticmethod
    def get_by_id(db: Session, note_id: int, user_id: int) -> Optional[models.Note]:
        """Получает заметку по ID"""
        return db.execute(
            select(models.Note).where(
                models.Note.id == note_id,
                models.Note.user_id == user_id
            )
        ).scalar_one_or_none()
    
    @staticmethod
    def get_by_date(db: Session, user_id: int, date: str) -> list[models.Note]:
        """Получает заметки за конкретную дату"""
        return db.execute(
            select(models.Note)
            .where(models.Note.user_id == user_id, models.Note.date == date)
            .order_by(models.Note.created_at.desc())
        ).scalars().all()
    
    @staticmethod
    def get_by_month(
        db: Session,
        user_id: int,
        year: int,
        month: int
    ) -> Dict[str, models.Note]:
        """
        Получает все заметки за указанный месяц.
        Возвращает словарь {date: note} для быстрого доступа.
        """
        # Создаем диапазон дат для месяца
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        notes = db.execute(
            select(models.Note)
            .where(
                models.Note.user_id == user_id,
                models.Note.date >= start_date.strftime('%Y-%m-%d'),
                models.Note.date < end_date.strftime('%Y-%m-%d')
            )
            .order_by(models.Note.date.desc(), models.Note.created_at.desc())
        ).scalars().all()
        
        # Группируем по датам, берем первую (самую новую) заметку для каждой даты
        notes_by_date = {}
        for note in notes:
            if note.date not in notes_by_date:
                notes_by_date[note.date] = note
        
        return notes_by_date
    
    @staticmethod
    def update(
        db: Session,
        note_id: int,
        user_id: int,
        content: str,
        date: str,
        mood: Optional[str] = None
    ) -> Optional[models.Note]:
        """Обновляет заметку"""
        note = NoteRepository.get_by_id(db, note_id, user_id)
        if not note:
            return None
        
        note.content = content
        note.date = date
        note.mood = mood
        db.commit()
        db.refresh(note)
        return note
    
    @staticmethod
    def delete(db: Session, note_id: int, user_id: int) -> bool:
        """Удаляет заметку"""
        note = NoteRepository.get_by_id(db, note_id, user_id)
        if not note:
            return False
        
        db.delete(note)
        db.commit()
        return True

