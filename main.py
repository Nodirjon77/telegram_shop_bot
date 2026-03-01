import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import API_TOKEN
from database.database import create_db

# 3 ta Routerni chaqiramiz
from handlers.admin import admin_router
from handlers.user import user_router
from handlers.common import common_router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ROUTER REGISTRATION ORDER (IMPORTANT!) ---
# 1. Admin (Highest priority commands)
dp.include_router(admin_router)

# 2. User (Menu and products)
dp.include_router(user_router)

# 3. Common (Start and other basic commands)
dp.include_router(common_router)

async def main():
    create_db()
    print("Bot started...")
    # Check the number of registered routers
    print(f"Connected routers: {len(dp.sub_routers)}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")