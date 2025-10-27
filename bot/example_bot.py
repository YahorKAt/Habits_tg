from dotenv import load_dotenv
load_dotenv()
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils import executor
import os


BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN environment variable is not set!")
    print("Please set it like: set BOT_TOKEN=your_bot_token_here")
    exit(1)

print(f"Using bot token: {BOT_TOKEN[:10]}...")
print(f"WebApp URL: {WEBAPP_URL}")

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=["start"]) 
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(text="Open Habits Mini App", web_app=WebAppInfo(url=WEBAPP_URL)))
    await message.answer("Open the Habits Mini App:", reply_markup=kb)


if __name__ == "__main__":
    print("Starting bot...")
    executor.start_polling(dp)




