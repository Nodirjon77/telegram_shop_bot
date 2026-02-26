from aiogram import Router, types, F
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice
from aiogram.types import ReplyKeyboardRemove

from keyboards.user_keyboards import get_main_menu
from config import ADMIN_ID, PAYMENT_TOKEN
# Keyboards va CallbackData
from keyboards.user_keyboards import (
    get_product_keyboard,
    get_contact_keyboard,
    get_payment_keyboard,
    get_cart_keyboard,
    get_categories_keyboard,
    CartCallback  # Yangi: CallbackData klassi
)

# States
from states.order_state import OrderState

# Database funksiyalari
from database.database import (
    add_to_cart,
    get_cart_products,
    clear_cart,
    get_product_count,
    update_cart_quantity,  # Yangi
    delete_cart_item,
    get_categories,
    get_products_by_category
)

user_router = Router()


@user_router.message(F.text == "🍔 Menyu")
async def show_categories(message: types.Message):
    categories = get_categories()

    if not categories:
        await message.answer("Hozircha bo'limlar mavjud emas 😔")
        return

    await message.answer("Iltimos, bo'limni tanlang: 👇",
                         reply_markup=get_categories_keyboard(categories))


# --- KATEGORIYA TANLANGANDA MAHSULOTLARNI CHIQARISH ---

@user_router.callback_query(F.data.startswith("category_"))
async def show_products_by_category(callback: types.CallbackQuery):
    category_name = callback.data.split("category_", 1)[1]
    products = get_products_by_category(category_name)

    # Eskisidan qolgan xabarni o'chirish (ixtiyoriy)
    await callback.message.delete()

    await callback.message.answer(f"📦 <b>{category_name}</b> bo'limidagi mahsulotlar:",
                                  parse_mode="HTML"
                                )

    for product in products:
        user_id = callback.from_user.id
        count = get_product_count(user_id, product['id'])
        keyboard = get_product_keyboard(product['id'], count)

        caption = f"<b>{product['name']}</b>\n\n💰 Narxi: {product['price']} so'm"
        await callback.message.answer_photo(
            photo=product['photo'],
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    await callback.answer()

# --- 2. SAVATGA QO'SHISH (MENU ICHIDAN) ---
@user_router.callback_query(F.data.startswith("add_"))
async def add_product_to_cart(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    add_to_cart(user_id, product_id)
    count = get_product_count(user_id, product_id)
    new_keyboard = get_product_keyboard(product_id, count)

    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=new_keyboard)

    await callback.answer(f"Savatga qo'shildi!")


# --- 3. SAVATNI KO'RISH ---
@user_router.message(F.text == "🗑 Savat")
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    cart_items = get_cart_products(user_id)

    if not cart_items:
        await message.answer("Savatingiz hozircha bo'sh 🗑")
        return

    text = "🛒 <b>Sizning savatingiz:</b>\n\n"
    total_price = 0

    for item in cart_items:
        # Bazadan 'quantity' va 'price' kelishi kerak
        line_total = item['price'] * item['quantity']
        total_price += line_total
        text += f"▪️ {item['name']} | {item['quantity']} ta | {line_total} so'm\n"

    text += f"\n💰 <b>Jami: {total_price} so'm</b>"

    await message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=get_cart_keyboard(cart_items)  # Dinamik tugmalar (+ / - / X)
    )


# --- 4. SAVAT ICHIDAGI AMALLAR (+, -, X) ---
@user_router.callback_query(CartCallback.filter())
async def handle_cart_actions(callback: types.CallbackQuery, callback_data: CartCallback):
    user_id = callback.from_user.id
    pid = callback_data.product_id
    action = callback_data.action

    # Logika: Bazani yangilash
    if action == "plus":
        update_cart_quantity(user_id, pid, 1)
    elif action == "minus":
        update_cart_quantity(user_id, pid, -1)
    elif action == "delete":
        delete_cart_item(user_id, pid)

    # Yangilangan ma'lumotlarni olish
    cart_items = get_cart_products(user_id)

    if not cart_items:
        await callback.message.edit_text("Savatingiz bo'shab qoldi 🗑")
        await callback.answer()
        return

    # Matnni qayta shakllantirish
    text = "🛒 <b>Sizning savatingiz:</b>\n\n"
    total_price = 0
    for item in cart_items:
        line_total = item['price'] * item['quantity']
        total_price += line_total
        text += f"▪️ {item['name']} | {item['quantity']} ta | {line_total} so'm\n"

    text += f"\n💰 <b>Jami: {total_price} so'm</b>"

    # Faqat o'zgargan qismini tahrirlash (ekran miltillab ketmasligi uchun)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=text,
            reply_markup=get_cart_keyboard(cart_items),
            parse_mode="HTML"
        )
    await callback.answer()


# --- 5. SAVATNI TOZALASH ---
@user_router.callback_query(F.data == "clear_cart")
async def process_clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    clear_cart(user_id)
    await callback.message.edit_text("Savatingiz tozalandi! 🗑")
    await callback.answer("Savat bo'shatildi")


# --- 6. BUYURTMA BERISH JARAYONI ---
@user_router.callback_query(F.data == "order")
async def ask_phone_number(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cart_items = get_cart_products(user_id)

    if not cart_items:
        await callback.answer("Savatingiz bo'sh!", show_alert=True)
        return

    await state.set_state(OrderState.waiting_for_phone)
    await callback.message.answer(
        "Buyurtmani rasmiylashtirish uchun telefon raqamingizni yuboring 📞\n"
        "Pastdagi tugmani bosing 👇",
        reply_markup=get_contact_keyboard()
    )
    with suppress(TelegramBadRequest):
        await callback.message.delete()

@user_router.message(OrderState.waiting_for_phone)
async def ask_payment_type(message: types.Message, state: FSMContext):
    # 1. Raqamni olamiz
    phone = message.contact.phone_number if message.contact else message.text

    # 2. Raqamni eslab qolamiz
    await state.update_data(phone=phone)

    # 3. Holatni o'zgartiramiz
    await state.set_state(OrderState.waiting_for_payment)

    # 4. To'lov turini so'raymiz va Reply Keyboard'ni o'chirib yuboramiz
    await message.answer(
        "Rahmat! Endi to'lov turini tanlang: 👇",
        reply_markup=get_payment_keyboard()
    )

    # MUHIM: Raqam yuborish tugmasini o'chirib tashlash uchun alohida xabar yoki
    # yuqoridagi xabarga ReplyKeyboardRemove qo'shish mumkin.
    # Lekin InlineKeyboardMarkup bilan ReplyKeyboardRemove birga ishlamasligi mumkin.
    # Shuning uchun bitta bo'sh xabar bilan tugmani yashiramiz:
    await message.answer("To'lov usulini tanlash uchun pastdagi tugmalardan foydalaning.",
                         reply_markup=ReplyKeyboardRemove())

# --- 7. TO'LOV TURINI QABUL QILISH ---

# A) NAQD PULNI TANLAGANDA
@user_router.callback_query(F.data == "pay_cash", OrderState.waiting_for_payment)
async def process_pay_cash(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    phone = user_data.get("phone")
    user_id = callback.from_user.id

    cart_items = get_cart_products(user_id)

    # Adminga hisobot tayyorlash
    order_text = f"🆕 <b>YANGI BUYURTMA (NAQD)!</b>\n\n"
    order_text += f"👤 Mijoz: {callback.from_user.full_name}\n"
    order_text += f"📞 Tel: {phone}\n"
    order_text += f"------------------------\n"

    total = 0
    for item in cart_items:
        summa = item['price'] * item['quantity']
        total += summa
        order_text += f"▪️ {item['name']} x {item['quantity']} = {summa} so'm\n"

    order_text += f"------------------------\n"
    order_text += f"💰 Jami: {total} so'm"

    # Adminga yuborish
    await callback.bot.send_message(ADMIN_ID, order_text, parse_mode="HTML")

    # Mijozga javob
    await callback.message.edit_text("✅ Buyurtmangiz qabul qilindi (Naqd to'lov). Rahmat!")
    await callback.message.answer("Asosiy menyu:", reply_markup=get_main_menu())

    clear_cart(user_id)
    await state.clear()
    await callback.answer()

# B) ONLINE TO'LOV (CLICK/PAYME) TANLAGANDA
@user_router.callback_query(F.data == "pay_card", OrderState.waiting_for_payment)
async def process_pay_card(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart_items = get_cart_products(user_id)

    prices = []
    for item in cart_items:
        # Telegram Payments summani tiyinlarda qabul qiladi (masalan: 1000 so'm = 100000 tiyin)
        prices.append(LabeledPrice(label=item['name'], amount=int(item['price'] * item['quantity'] * 100)))

    await callback.message.answer_invoice(
        title="Buyurtma uchun to'lov",
        description="Tanlangan mahsulotlar uchun online to'lov",
        payload="order_payload_123",  # Ichki ID
        provider_token=PAYMENT_TOKEN,
        currency="UZS",
        prices=prices,
        start_parameter="shop_bot_payment"
    )
    await callback.answer()


# --- 8. TELEGRAM PAYMENTS MAHSUS HANDLERLARI ---

# To'lov tugmasi bosilganda (Pre-Checkout)
@user_router.pre_checkout_query()
async def checkout_process(pre_checkout_q: types.PreCheckoutQuery):
    await pre_checkout_q.answer(ok=True)


@user_router.message(F.successful_payment)
async def on_successful_payment(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    phone = user_data.get("phone", "Noma'lum")

    pay_info = message.successful_payment  # To'lov haqida ma'lumotlar

    # 1. Adminga to'liq chek shakllantiramiz
    admin_msg = (
        f"💰 <b>YANGI ONLINE TO'LOV!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Mijoz:</b> {message.from_user.full_name}\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"📞 <b>Tel:</b> {phone}\n"
        f"💵 <b>Summa:</b> {pay_info.total_amount // 100} {pay_info.currency}\n"
        f"📑 <b>Tranzaksiya ID:</b> \n<code>{pay_info.provider_payment_charge_id}</code>\n"
        f"📅 <b>Sana:</b> {message.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ To'lov muvaffaqiyatli tasdiqlandi."
    )

    # 2. Adminga yuboramiz
    await message.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="HTML")

    # 3. Mijozga tasdiq xabari
    await message.answer(
        f"Rahmat! <b>{pay_info.total_amount // 100} so'm</b> miqdoridagi to'lovingiz qabul qilindi. ✅\n"
        f"Buyurtmangiz tayyorlanmoqda.",
        parse_mode="HTML"
    )

    # Savatni tozalash va holatni yakunlash
    clear_cart(user_id)
    await state.clear()
    await message.answer("Asosiy menyuga qaytdingiz:", reply_markup=get_main_menu())