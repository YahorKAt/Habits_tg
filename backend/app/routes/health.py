"""
Роутеры для проверки работоспособности API
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import sys
import logging

from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    """Базовая проверка работоспособности API"""
    logger.debug("🔍 Проверка работоспособности API (health check)")
    return JSONResponse({
        "status": "ok",
        "message": "API is running"
    })


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> JSONResponse:
    """Проверка подключения к базе данных"""
    logger.info("🔍 Проверка подключения к базе данных...")
    try:
        db.execute(text("SELECT 1"))
        db.commit()
        logger.info("✅ База данных доступна")
        return JSONResponse({
            "status": "ok",
            "database": "connected"
        })
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {e}", exc_info=True)
        return JSONResponse({
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }, status_code=500)


@router.get("/health/full")
def health_full() -> JSONResponse:
    """Полная диагностика системы"""
    diagnostics = {
        "status": "ok",
        "python_version": sys.version,
        "dev_mode": os.getenv("DEV_MODE", "not set"),
        "dev_user_id": os.getenv("DEV_USER_ID", "not set"),
        "bot_token_set": "yes" if os.getenv("BOT_TOKEN") else "no",
        "database_url": os.getenv("DATABASE_URL", "using default"),
    }
    
    # Проверка импортов
    try:
        from telegram_webapp_auth.data import WebAppChat
        diagnostics["telegram_webapp_auth"] = "imported"
    except ImportError as e:
        diagnostics["telegram_webapp_auth"] = f"import failed: {str(e)}"
    
    try:
        from sqlalchemy import create_engine
        diagnostics["sqlalchemy"] = "imported"
    except ImportError as e:
        diagnostics["sqlalchemy"] = f"import failed: {str(e)}"
    
    return JSONResponse(diagnostics)


@router.post("/migrate")
def run_migrations_endpoint(db: Session = Depends(get_db)) -> JSONResponse:
    """Ручной запуск миграций базы данных"""
    logger.info("🔄 Запуск миграций базы данных...")
    try:
        from .. import migrations
        migrations.migrate_all(db)
        logger.info("✅ Миграции успешно применены")
        return JSONResponse({
            "status": "ok",
            "message": "Migrations applied successfully"
        })
    except Exception as e:
        logger.error(f"❌ Ошибка применения миграций: {e}", exc_info=True)
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

