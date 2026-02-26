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

# --- ROUTERLARNI ULASH TARTIBI (MUHIM!) ---
# 1. Admin (Eng muhim buyruqlar)
dp.include_router(admin_router)

# 2. User (Menyu va tovarlar)
dp.include_router(user_router)

# 3. Common (Start va qolgan oddiy gaplar)
dp.include_router(common_router)


async def main():
    create_db()
    print("Bot ishga tushdi...")
    # Routerlar ro'yxatini ko'rib qo'yamiz
    print(f"Ulangan routerlar: {len(dp.sub_routers)} ta")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtadi")