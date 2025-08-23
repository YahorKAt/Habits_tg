from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from .database import init_db, get_db
from .schemas import TaskCreate, SubtaskCreate
from . import crud
from sqlalchemy.orm import Session
import os

from .telegram_auth import parse_and_validate_init_data


app = FastAPI(title="Habits Mini App API")

origins = [
    "http://localhost:5173", #"http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://*.telegram.org",
    "https://webapp.bot",
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
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    if dev_mode:
        return int(os.getenv("DEV_USER_ID", "1"))
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram init data")
    user = parse_and_validate_init_data(x_telegram_init_data)
    if not user or "id" not in user:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")
    return int(user["id"])  # type: ignore


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/task")
def add_task(payload: TaskCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    task = crud.create_task(db, user_id=user_id, title=payload.title)
    return task


@app.post("/subtask")
def add_subtask(payload: SubtaskCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    task = crud.get_task(db, task_id=payload.task_id, user_id=user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    subtask = crud.create_subtask(db, task_id=payload.task_id, title=payload.title)
    return subtask


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




