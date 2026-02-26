from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
import asyncio

from aiogram.exceptions import TelegramForbiddenError
from config import ADMIN_ID
from database.database import add_product, get_all_products, delete_product_from_db, get_all_users
from states.admin_state import AdminState

admin_router = Router()


# --- 1. ADMIN PANEL TUGMALARI ---
def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="❌ Mahsulot o'chirish")],
            [KeyboardButton(text="📢 Reklama yuborish")],
            [KeyboardButton(text="🏠 Bosh sahifa (User rejimi)")]
        ],
        resize_keyboard=True
    )


# --- 2. ADMIN PANELGA KIRISH ---
@admin_router.message(Command("admin"))
async def admin_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Siz admin emassiz ❌")
        return

    await state.clear()  # Eski holatlarni tozalaymiz
    await message.answer(
        "👨‍💻 <b>Admin Panelga xush kelibsiz!</b>\n\nQuyidagi tugmalar orqali boshqaring:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )


# --- 3. MAHSULOT QO'SHISH BOSQICHLARI ---

# A) "Mahsulot qo'shish" tugmasi bosilganda
@admin_router.message(F.text == "➕ Mahsulot qo'shish")
async def start_add_product(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return

    await message.answer("Yangi mahsulot nomini kiriting:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.waiting_for_name)


# B) Nomini qabul qilish
@admin_router.message(AdminState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Kategoriyani yozing (masalan: 🌳 Daraxtlar):")
    await state.set_state(AdminState.waiting_for_category)


# C) Kategoriyani qabul qilish
@admin_router.message(AdminState.waiting_for_category)
async def process_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Narxini yozing (faqat raqam):")
    await state.set_state(AdminState.waiting_for_price)


# D) Narxini qabul qilish
@admin_router.message(AdminState.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam yozing!")
        return
    await state.update_data(price=int(message.text))
    await message.answer("Rasmini yuboring 📸")
    await state.set_state(AdminState.waiting_for_photo)


# E) Rasmni qabul qilish va SAQLASH
@admin_router.message(AdminState.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()

    add_product(data['name'], data['price'], photo_id, data['category'])

    await message.answer(
        f"✅ <b>Mahsulot qo'shildi!</b>\n\n{data['name']} - {data['price']} so'm",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()  # Admin menyuni qaytaramiz
    )
    await state.clear()


# --- 4. MAHSULOT O'CHIRISH BO'LIMI ---

@admin_router.message(F.text == "❌ Mahsulot o'chirish")
async def delete_menu_btn(message: types.Message):
    if message.from_user.id != ADMIN_ID: return

    products = get_all_products()
    if not products:
        await message.answer("O'chirish uchun mahsulot yo'q.")
        return

    builder = InlineKeyboardBuilder()
    for product in products:
        builder.row(InlineKeyboardButton(text=f"❌ {product['name']}", callback_data=f"del_prod_{product['id']}"))

    builder.row(InlineKeyboardButton(text="🚪 Bekor qilish", callback_data="close_del"))

    await message.answer("Qaysi birini o'chirasiz?", reply_markup=builder.as_markup())


# O'chirish logikasi
@admin_router.callback_query(F.data.startswith("del_prod_"))
async def process_delete(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[2])
    delete_product_from_db(pid)
    await callback.answer("O'chirildi! 🗑")

    # Ro'yxatni yangilash
    products = get_all_products()
    if not products:
        await callback.message.edit_text("Mahsulotlar qolmadi.", reply_markup=None)
        return

    builder = InlineKeyboardBuilder()
    for product in products:
        builder.row(InlineKeyboardButton(text=f"❌ {product['name']}", callback_data=f"del_prod_{product['id']}"))
    builder.row(InlineKeyboardButton(text="🚪 Bekor qilish", callback_data="close_del"))

    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())


@admin_router.callback_query(F.data == "close_del")
async def close_del_window(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("O'chirish menyusi yopildi.")


# --- 5. ADMIN REJIMIDAN CHIQISH ---
from keyboards.user_keyboards import get_main_menu  # User menyusini import qilamiz


@admin_router.message(F.text == "🏠 Bosh sahifa (User rejimi)")
async def exit_admin(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Siz foydalanuvchi rejimiga o'tdingiz.", reply_markup=get_main_menu())

@admin_router.message(F.text == "📢 Reklama yuborish")
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return

    await message.answer("Barchaga yuboriladigan xabarni yozing (rasm, video yoki matn bo'lishi mumkin):",
                         reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.waiting_for_broadcast_message)


@admin_router.message(AdminState.waiting_for_broadcast_message)
async def send_broadcast(message: types.Message, state: FSMContext):
    users = get_all_users()

    if not users:
        await message.answer("Bazada hech kim yo'q.", reply_markup=get_admin_keyboard())
        await state.clear()
        return

    await message.answer(f"Reklama {len(users)} ta foydalanuvchiga yuborilmoqda... Kuting ⏳")

    success = 0
    fail = 0

    for user_id in users:
        try:
            # message.copy_to() - bu eng zo'r usul. U matnni ham, rasmni ham aslicha ko'chirib yuboradi.
            await message.copy_to(chat_id=user_id)
            success += 1
            await asyncio.sleep(0.05)  # Telegram bloklamasligi uchun kichik pauza (antispam)
        except TelegramForbiddenError:
            # Agar foydalanuvchi botni bloklagan bo'lsa xato beradi
            fail += 1

    await message.answer(
        f"✅ <b>Reklama yuborish yakunlandi!</b>\n\n"
        f"Muvaffaqiyatli: {success} ta\n"
        f"Yetib bormadi (botni bloklaganlar): {fail} ta",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()