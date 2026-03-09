from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from database.database import add_user

common_router = Router()


# --- KEYBOARDS ---
def get_main_menu():
    keyboard = [
        [KeyboardButton(text="🍔 Menu"), KeyboardButton(text="🛒 Cart")],
        [KeyboardButton(text="📞 Contact Us"), KeyboardButton(text="ℹ️ About Us")],
        [KeyboardButton(text="📍 Our Location")]
    ]
    # resize_keyboard=True makes the buttons look compact and professional
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# --- START COMMAND ---
@common_router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Register the user in the database upon first contact
    add_user(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )

    await message.answer(
        f"Welcome, {message.from_user.first_name}! 👋\n"
        f"Welcome to our shop. How can we help you today?",
        reply_markup=get_main_menu()
    )


# --- COMMON MESSAGE HANDLERS ---
@common_router.message()
async def handle_common_messages(message: types.Message):
    text = message.text

    if text == "🛒 Cart":
        # Note: Actual cart logic is handled in user_handlers.py,
        # but we keep this as a fallback if the cart is empty.
        await message.answer("Your cart is currently empty 🗑")

    elif text == "📞 Contact Us":
        await message.answer("Support Admin: @NodirJON_NURIDIN 👨‍💻")

    elif text == "ℹ️ About Us":
        await message.answer(
            "Welcome to our premium online shop! 😎\n"
            "We provide high-quality products with fast delivery."
        )

    elif text == "📍 Our Location":
        await message.answer(
            "📍 We are located in: Uzbekistan district, Dungsaroy.\n"
            "Come visit us or order online! 🏠"
        )