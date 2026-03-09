from aiogram import Router, types, F
from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice, ReplyKeyboardRemove

from keyboards.user_keyboards import get_main_menu
from config import ADMIN_ID, PAYMENT_TOKEN
# Keyboards and CallbackData
from keyboards.user_keyboards import (
    get_product_keyboard,
    get_contact_keyboard,
    get_payment_keyboard,
    get_cart_keyboard,
    get_categories_keyboard,
    CartCallback
)

# States
from states.order_state import OrderState

# Database functions
from database.database import (
    add_to_cart,
    get_cart_products,
    clear_cart,
    get_product_count,
    update_cart_quantity,
    delete_cart_item,
    get_categories,
    get_products_by_category,
    reduce_product_quantity,
    get_product_quantity
)

user_router = Router()

# --- 1. CATEGORY SELECTION ---
@user_router.message(F.text == "🍔 Menu")
async def show_categories(message: types.Message):
    categories = get_categories()

    if not categories:
        await message.answer("No categories available at the moment 😔")
        return

    await message.answer("Please select a category: 👇",
                         reply_markup=get_categories_keyboard(categories))


# --- 2. SHOW PRODUCTS BY CATEGORY ---
@user_router.callback_query(F.data.startswith("category_"))
async def show_products_by_category(callback: types.CallbackQuery):
    category_name = callback.data.split("category_", 1)[1]
    products = get_products_by_category(category_name)

    # Delete the previous message for a cleaner UI
    await callback.message.delete()

    await callback.message.answer(f"📦 Products in <b>{category_name}</b>",
                                  parse_mode="HTML")

    for product in products:
        user_id = callback.from_user.id

        # Get current quantity in cart and available stock
        count = get_product_count(user_id, product['id']) or 0
        stock = product['quantity']

        keyboard = get_product_keyboard(product_id=product['id'], count=count, stock=stock)

        # Prepare product status info
        stock_info = f"📦 In Stock: {stock} pcs" if stock > 0 else "🔴 Out of Stock!"
        caption = f"<b>{product['name']}</b>\n\n💰 Price: {product['price']} USD\n{stock_info}"

        await callback.message.answer_photo(
            photo=product['photo'],
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    await callback.answer()


# --- 3. ADD TO CART ---
@user_router.callback_query(F.data.startswith("add_"))
async def add_product_to_cart(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    add_to_cart(user_id, product_id)
    count = get_product_count(user_id, product_id)
    stock = get_product_quantity(product_id)

    # Update inline keyboard with new count
    new_keyboard = get_product_keyboard(product_id=product_id, count=count, stock=stock)

    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=new_keyboard)

    await callback.answer("Added to Cart! ✅")


@user_router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    await callback.answer("Stock limit reached or item unavailable!", show_alert=True)


# --- 4. VIEW CART ---
@user_router.message(F.text == "🛒 Cart")
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    cart_items = get_cart_products(user_id)

    if not cart_items:
        await message.answer("Your cart is currently empty 🗑")
        return

    text = "🛒 <b>Your Cart:</b>\n\n"
    total_price = 0

    for item in cart_items:
        line_total = item['price'] * item['quantity']
        total_price += line_total
        text += f"▪️ {item['name']} | {item['quantity']} pcs | {line_total} USD\n"

    text += f"\n💰 <b>Total: {total_price} USD</b>"

    await message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=get_cart_keyboard(cart_items)
    )


# --- 5. CART ACTIONS (+, -, X) ---
@user_router.callback_query(CartCallback.filter())
async def handle_cart_actions(callback: types.CallbackQuery, callback_data: CartCallback):
    user_id = callback.from_user.id
    pid = callback_data.product_id
    action = callback_data.action

    # Update database based on action
    if action == "plus":
        update_cart_quantity(user_id, pid, 1)
    elif action == "minus":
        update_cart_quantity(user_id, pid, -1)
    elif action == "delete":
        delete_cart_item(user_id, pid)

    cart_items = get_cart_products(user_id)

    if not cart_items:
        await callback.message.edit_text("Cart is now empty! 🗑")
        await callback.answer()
        return

    # Reconstruct the cart text
    text = "🛒 <b>Your Cart:</b>\n\n"
    total_price = 0
    for item in cart_items:
        line_total = item['price'] * item['quantity']
        total_price += line_total
        text += f"▪️ {item['name']} | {item['quantity']} pcs | {line_total} USD\n"

    text += f"\n💰 <b>Total: {total_price} USD</b>"

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=text,
            reply_markup=get_cart_keyboard(cart_items),
            parse_mode="HTML"
        )
    await callback.answer()


# --- 6. CLEAR CART ---
@user_router.callback_query(F.data == "clear_cart")
async def process_clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    clear_cart(user_id)
    await callback.message.edit_text("Cart cleared! 🗑")
    await callback.answer("Cart has been cleared.")


# --- 7. ORDERING PROCESS ---
@user_router.callback_query(F.data == "order")
async def ask_phone_number(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cart_items = get_cart_products(user_id)

    if not cart_items:
        await callback.answer("Your cart is empty!", show_alert=True)
        return

    await state.set_state(OrderState.waiting_for_phone)
    await callback.message.answer(
        "Please share your phone number to proceed with the checkout 📞\n"
        "Click the button below 👇",
        reply_markup=get_contact_keyboard()
    )
    with suppress(TelegramBadRequest):
        await callback.message.delete()

@user_router.message(OrderState.waiting_for_phone)
async def ask_payment_type(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    await state.set_state(OrderState.waiting_for_payment)

    await message.answer(
        "Thank you! Now please select a payment method: 👇",
        reply_markup=get_payment_keyboard()
    )
    # Remove the contact request keyboard
    await message.answer("Processing...", reply_markup=ReplyKeyboardRemove())

# --- 8. PAYMENT METHODS ---

# A) CASH ON DELIVERY
@user_router.callback_query(F.data == "pay_cash", OrderState.waiting_for_payment)
async def process_pay_cash(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    phone = user_data.get("phone")
    user_id = callback.from_user.id
    cart_items = get_cart_products(user_id)

    # Prepare report for Admin
    order_text = f"🆕 <b>NEW ORDER (CASH)!</b>\n\n"
    order_text += f"👤 Customer: {callback.from_user.full_name}\n"
    order_text += f"📞 Phone: {phone}\n"
    order_text += f"------------------------\n"

    total = 0
    for item in cart_items:
        summa = item['price'] * item['quantity']
        total += summa
        order_text += f"▪️ {item['name']} x {item['quantity']} = {summa} USD\n"
        reduce_product_quantity(item['id'], item['quantity'])

    order_text += f"------------------------\n"
    order_text += f"💰 Total: {total} USD"

    await callback.bot.send_message(ADMIN_ID, order_text, parse_mode="HTML")
    await callback.message.edit_text("✅ Your order has been received (Cash Payment). Thank you!")
    await callback.message.answer("Main Menu:", reply_markup=get_main_menu())

    clear_cart(user_id)
    await state.clear()
    await callback.answer()

# B) ONLINE CARD PAYMENT
@user_router.callback_query(F.data == "pay_card", OrderState.waiting_for_payment)
async def process_pay_card(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart_items = get_cart_products(user_id)

    prices = []
    for item in cart_items:
        prices.append(LabeledPrice(label=item['name'], amount=int(item['price'] * item['quantity'] * 100)))

    await callback.message.answer_invoice(
        title="Order Payment",
        description="Online payment for your order",
        payload="order_id_unique",
        provider_token=PAYMENT_TOKEN,
        currency="UZS",
        prices=prices,
        start_parameter="shop_payment"
    )
    await callback.answer()


# --- 9. TELEGRAM PAYMENT HANDLERS ---

@user_router.pre_checkout_query()
async def checkout_process(pre_checkout_q: types.PreCheckoutQuery):
    await pre_checkout_q.answer(ok=True)


@user_router.message(F.successful_payment)
async def on_successful_payment(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    phone = user_data.get("phone", "Unknown")

    pay_info = message.successful_payment

    # Admin notification
    admin_msg = (
        f"💰 <b>NEW ONLINE PAYMENT!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Customer:</b> {message.from_user.full_name}\n"
        f"📞 <b>Phone:</b> {phone}\n"
        f"💵 <b>Amount:</b> {pay_info.total_amount // 100} {pay_info.currency}\n"
        f"📑 <b>Transaction ID:</b> \n<code>{pay_info.provider_payment_charge_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    await message.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="HTML")
    await message.answer(f"Payment received! ✅ Amount: <b>{pay_info.total_amount // 100} USD</b>", parse_mode="HTML")

    # Stock reduction logic
    cart_items = get_cart_products(user_id)
    for item in cart_items:
        reduce_product_quantity(item['id'], item['quantity'])

    clear_cart(user_id)
    await state.clear()
    await message.answer("Returned to Main Menu:", reply_markup=get_main_menu())