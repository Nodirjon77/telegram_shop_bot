from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from database.database import add_user

common_router = Router()


# --- TUGMALAR ---
def get_main_menu():
    keyboard = [
        [KeyboardButton(text="🍔 Menyu"), KeyboardButton(text="🗑 Savat")],
        [KeyboardButton(text="📞 Biz bilan aloqa"), KeyboardButton(text="ℹ️ Biz haqimizda")],
        [KeyboardButton(text="📍 Manzilimiz")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# --- START ---
@common_router.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )

    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}! \n"
        f"Do'konimizga xush kelibsiz.",
        reply_markup=get_main_menu()
    )


# --- BOSHQA TUGMALAR ---
# (Menyu tugmasi user.py da, shuning uchun bu yerda yozmaymiz)
@common_router.message()
async def handle_common_messages(message: types.Message):
    text = message.text

    if text == "🗑 Savat":
        await message.answer("Savatingiz bo'sh.")
    elif text == "📞 Biz bilan aloqa":
        await message.answer("Admin: @NodirJON_NURIDIN")
    elif text == "ℹ️ Biz haqimizda":
        await message.answer("Biz eng zo'r do'konmiz! 😎")
    elif text == "📍 Manzilimiz":
        await message.answer("Biz Do'ngsaroydamiz! 🏠")
    # "Menyu" so'ziga bu yerda javob bermaymiz, chunki u user.py da ishlaydi