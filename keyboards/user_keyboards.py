from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData


# 1. Savatdagi amallar uchun CallbackData Factory
class CartCallback(CallbackData, prefix="cart"):
    action: str  # 'plus', 'minus', 'delete'
    product_id: int


# 2. Savat uchun dinamik tugmalar generatori
def get_cart_keyboard(cart_items):
    builder = InlineKeyboardBuilder()

    for item in cart_items:
        # item['id'], item['name'], item['quantity'] bazadan keladi
        pid = item['id']
        name = item['name']
        qty = item['quantity']

        # Birinchi qator: Mahsulot nomi va o'chirish tugmasi
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {name}",
                callback_data=CartCallback(action="delete", product_id=pid).pack()
            )
        )
        # Ikkinchi qator: Minus, Miqdor, Plus
        builder.row(
            InlineKeyboardButton(
                text="➖",
                callback_data=CartCallback(action="minus", product_id=pid).pack()
            ),
            InlineKeyboardButton(
                text=f"{qty} pcs",
                callback_data="ignore"  # Bu tugma shunchaki ma'lumot uchun
            ),
            InlineKeyboardButton(
                text="➕",
                callback_data=CartCallback(action="plus", product_id=pid).pack()
            )
        )

    # Pastki umumiy tugmalar
    builder.row(InlineKeyboardButton(text="🛍 Checkout", callback_data="order"))
    builder.row(InlineKeyboardButton(text="🗑 Clear Cart", callback_data="clear_cart"))

    return builder.as_markup()


# 3. Menyu uchun tugmalar (har bir mahsulot ostida)
def get_product_keyboard(product_id, count=0, stock=0):

    builder = InlineKeyboardBuilder()

    # Toza raqamga o'giramiz (agar bu yerda xatolik bo'lsa, terminalda qizil yozuv chiqadi va aybdorni topamiz)
    count = int(count) if count else 0
    stock = int(stock) if stock else 0

    # 1-holat: Omborda umuman qolmagan
    if stock <= 0:
        builder.add(InlineKeyboardButton(text="🚫 Out of Stock", callback_data="ignore"))

    # 2-holat: Mijoz ombordagi barcha bor zaxirani savatga qo'shib bo'lgan (limit)
    elif count >= stock:
        builder.add(InlineKeyboardButton(text=f"✅ In Cart (Max {count})", callback_data="ignore"))

    # 3-holat: Hali omborda joy bor, bemalol qo'shishi mumkin
    else:
        if count > 0:
            builder.add(InlineKeyboardButton(text=f"✅ In Cart ({count}) ➕", callback_data=f"add_{product_id}"))
        else:
            builder.add(InlineKeyboardButton(text="🛒 Add to Cart", callback_data=f"add_{product_id}"))

    return builder.as_markup()

# 4. Kontakt yuborish tugmasi
def get_contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Share Contact", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# 5. To'lov turi tugmalari
def get_payment_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💵 Cash on Delivery", callback_data="pay_cash"))
    builder.row(InlineKeyboardButton(text="💳 Online Payment", callback_data="pay_card"))
    return builder.as_markup()

# 6. Asosiy menyu tugmalari
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍔 Menu")],
            [KeyboardButton(text="🛒 Cart"), KeyboardButton(text="👤 My Account")] # Profil ixtiyoriy
        ],
        resize_keyboard=True
    )

def get_categories_keyboard(categories):
    builder = InlineKeyboardBuilder()
    for category in categories:
        # Har bir kategoriya uchun alohida tugma
        builder.row(InlineKeyboardButton(text=category, callback_data=f"category_{category}"))
    return builder.as_markup()