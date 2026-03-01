from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
import asyncio

from aiogram.exceptions import TelegramForbiddenError
from config import ADMIN_ID
from database.database import add_product, get_all_products, delete_product_from_db, get_all_users, get_all_products_admin, update_product_quantity
from states.admin_state import AdminState

admin_router = Router()

# --- 1. ADMIN PANEL TUGMALARI ---
def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Add Product"), KeyboardButton(text="❌ Delete Product")],
            [KeyboardButton(text="✏️ Restock"), KeyboardButton(text="📢 Send Broadcast")],
            [KeyboardButton(text="🏠 Home (User Mode)")]
        ],
        resize_keyboard=True
    )

# --- 2. ADMIN PANELGA KIRISH ---
@admin_router.message(Command("admin"))
async def admin_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("You are not an admin ❌")
        return

    await state.clear()
    await message.answer(
        "👨‍💻 <b>Welcome to the Admin Panel!</b>\n\nUse the buttons below to manage:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

# --- 3. MAHSULOT QO'SHISH BOSQICHLARI ---

@admin_router.message(F.text == "➕ Add Product")
async def start_add_product(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return

    await message.answer("Enter the name of the new product:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.waiting_for_name)

@admin_router.message(AdminState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Enter the category (e.g., 🌳 Trees):")
    await state.set_state(AdminState.waiting_for_category)

@admin_router.message(AdminState.waiting_for_category)
async def process_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Enter the price (numbers only):")
    await state.set_state(AdminState.waiting_for_price)

@admin_router.message(AdminState.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Please enter numbers only!")
        return
    await state.update_data(price=int(message.text))
    await message.answer("Send a photo of the product 📸")
    await state.set_state(AdminState.waiting_for_photo)

@admin_router.message(AdminState.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)

    await message.answer("📦 How many items are in stock? (Numbers only)")
    await state.set_state(AdminState.waiting_for_quantity)

@admin_router.message(AdminState.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Please enter numbers only!\nHow many are in stock?")
        return

    quantity = int(message.text)
    data = await state.get_data()

    add_product(data['name'], data['price'], data['photo'], data['category'], quantity)

    # Qaysi javob noto'g'ri joyda ketganini to'g'irladim.
    # Shuningdek, xabar qismini ham yangiladim. (O'zbekchada F qismida returnni joyida xato ketibdi yozuv).
    await message.answer(
        f"✅ <b>Product successfully added to the inventory!</b>\n\n"
        f"🏷 Name: {data['name']}\n"
        f"💰 Price: {data['price']} UZS\n"
        f"📦 In Stock: {quantity} pcs",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@admin_router.message(F.text == "✏️ Restock")
async def show_products_for_restock(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    products = get_all_products_admin()
    if not products:
        await message.answer("There are no products in the database 🤷‍♂️")
        return

    builder = InlineKeyboardBuilder()
    for p in products:
        btn_text = f"📦 {p['name']} (Stock: {p['quantity']} pcs)"
        builder.add(InlineKeyboardButton(text=btn_text, callback_data=f"restock_{p['id']}"))

    builder.adjust(1)
    await message.answer("Which product's stock would you like to update? Select below 👇", reply_markup=builder.as_markup())

# --- 3. ZAXIRANI TO'LDIRISH ---
@admin_router.callback_query(F.data.startswith("restock_"))
async def process_restock_callback(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    await state.update_data(restock_product_id=product_id)

    await callback.message.answer("📦 Enter the NEW total quantity for this product (numbers only):")
    await state.set_state(AdminState.waiting_for_edit_quantity)
    await callback.answer()

@admin_router.message(AdminState.waiting_for_edit_quantity)
async def save_new_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Please enter numbers only!")
        return

    new_quantity = int(message.text)
    data = await state.get_data()
    product_id = data.get("restock_product_id")

    update_product_quantity(product_id, new_quantity)

    await state.clear()
    await message.answer(f"✅ Stock updated successfully!\nThere are now {new_quantity} pcs in stock.")

# --- 4. MAHSULOT O'CHIRISH BO'LIMI ---
@admin_router.message(F.text == "❌ Delete Product")
async def delete_menu_btn(message: types.Message):
    if message.from_user.id != ADMIN_ID: return

    products = get_all_products()
    if not products:
        await message.answer("No products available to delete.")
        return

    builder = InlineKeyboardBuilder()
    for product in products:
        builder.row(InlineKeyboardButton(text=f"❌ {product['name']}", callback_data=f"del_prod_{product['id']}"))

    builder.row(InlineKeyboardButton(text="🚪 Cancel", callback_data="close_del"))
    await message.answer("Which one would you like to delete?", reply_markup=builder.as_markup())

@admin_router.callback_query(F.data.startswith("del_prod_"))
async def process_delete(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[2])
    delete_product_from_db(pid)
    await callback.answer("Deleted! 🗑")

    products = get_all_products()
    if not products:
        await callback.message.edit_text("No products left.", reply_markup=None)
        return

    builder = InlineKeyboardBuilder()
    for product in products:
        builder.row(InlineKeyboardButton(text=f"❌ {product['name']}", callback_data=f"del_prod_{product['id']}"))
    builder.row(InlineKeyboardButton(text="🚪 Cancel", callback_data="close_del"))

    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())

@admin_router.callback_query(F.data == "close_del")
async def close_del_window(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Delete menu closed.")

# --- 5. ADMIN REJIMIDAN CHIQISH ---
from keyboards.user_keyboards import get_main_menu

@admin_router.message(F.text == "🏠 Home (User Mode)")
async def exit_admin(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("You have switched to User mode.", reply_markup=get_main_menu())

# --- 6. REKLAMA YUBORISH ---
@admin_router.message(F.text == "📢 Send Broadcast")
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return

    await message.answer("Enter the broadcast message (can be text, photo, or video):",
                         reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.waiting_for_broadcast_message)

@admin_router.message(AdminState.waiting_for_broadcast_message)
async def send_broadcast(message: types.Message, state: FSMContext):
    users = get_all_users()

    if not users:
        await message.answer("No users found in the database.", reply_markup=get_admin_keyboard())
        await state.clear()
        return

    await message.answer(f"Sending broadcast to {len(users)} users... Please wait ⏳")

    success = 0
    fail = 0

    for user_id in users:
        try:
            await message.copy_to(chat_id=user_id)
            success += 1
            await asyncio.sleep(0.05)
        except TelegramForbiddenError:
            fail += 1

    await message.answer(
        f"✅ <b>Broadcast finished!</b>\n\n"
        f"Successful: {success}\n"
        f"Failed (blocked bot): {fail}",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()