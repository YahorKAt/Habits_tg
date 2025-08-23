## Backend (FastAPI)

Run locally:

```bash
python -m venv .venv && .venv\\Scripts\\activate
pip install -r requirements.txt
set DEV_MODE=true && set DEV_USER_ID=1 && set BOT_TOKEN=8294461897:AAGmR53gKOlz1-O8c-1aDRh6prSoLIrS0TQ
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Environment:
- BOT_TOKEN: Telegram Bot token (for WebApp auth check). In DEV_MODE it can be dummy.
- DEV_MODE=true enables skipping strict auth using `DEV_USER_ID`.



