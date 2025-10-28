from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from .database import init_db, get_db
from .schemas import TaskCreate, SubtaskCreate, NoteCreate
from . import crud
import logging
from sqlalchemy.orm import Session
import os


from .telegram_auth import parse_and_validate_init_data

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Habits Mini App API")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://*.telegram.org",
    "https://t.me",
    "https://webapp.bot",
    "https://habits-tg.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def get_user_id(x_telegram_init_data: str | None = Header(default=None)) -> int:
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram init data")
    user = parse_and_validate_init_data(x_telegram_init_data)
    if not user or "id" not in user:
        print("Не нашёл данных X-Telegram-Init-Data received:", x_telegram_init_data)
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")
    return int(user["id"])  # type: ignore


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/task")
def add_task(payload: TaskCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    try:
        logger.info(f"Creating task: title={payload.title}, category={payload.category}, frequency={payload.frequency}")
        task = crud.create_task(
            db, 
            user_id=user_id, 
            title=payload.title,
            description=payload.description,
            repeat_type=payload.repeat_type,
            repeat_interval=payload.repeat_interval,
            next_due_date=payload.next_due_date,
            end_date=payload.end_date,
            category=payload.category,
            frequency=payload.frequency
        )
        logger.info(f"Task created successfully with id={task.id}")
        return task
    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@app.put("/task/{task_id}")
def update_task(task_id: int, payload: TaskCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    task = crud.update_task(
        db, 
        task_id=task_id,
        user_id=user_id, 
        title=payload.title,
        description=payload.description,
        repeat_type=payload.repeat_type,
        repeat_interval=payload.repeat_interval,
        next_due_date=payload.next_due_date,
        end_date=payload.end_date,
        category=payload.category,
        frequency=payload.frequency
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/subtask")
def add_subtask(payload: SubtaskCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    task = crud.get_task(db, task_id=payload.task_id, user_id=user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    subtask = crud.create_subtask(db, task_id=payload.task_id, title=payload.title)
    return subtask


@app.delete("/subtask/{subtask_id}")
def delete_subtask(subtask_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    deleted = crud.delete_subtask(db, subtask_id=subtask_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return {"ok": True}


@app.delete("/task/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    deleted = crud.delete_task(db, task_id=task_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}


@app.get("/tasks")
def list_tasks(db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    return crud.list_tasks_with_subtasks(db, user_id=user_id)


@app.post("/task/{task_id}/complete")
def complete_task(task_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    task = crud.set_task_completed(db, task_id=task_id, user_id=user_id, completed=True)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/subtask/{subtask_id}/complete")
def complete_subtask(subtask_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    subtask = crud.set_subtask_completed(db, subtask_id=subtask_id, user_id=user_id, completed=True)
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return subtask


@app.get("/stats")
def stats(period: str, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    if period not in {"7", "30", "all"}:
        raise HTTPException(status_code=400, detail="Invalid period")
    return crud.get_stats(db, user_id=user_id, period=period)


@app.post("/notes")
def add_note(payload: NoteCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    note = crud.create_note(
        db, 
        user_id=user_id, 
        content=payload.content,
        date=payload.date,
        mood=payload.mood
    )
    return note


@app.get("/notes")
def list_notes(date: str, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    return crud.get_notes_by_date(db, user_id=user_id, date=date)


@app.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    deleted = crud.delete_note(db, note_id=note_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}




