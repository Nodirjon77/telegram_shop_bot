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
                text=f"{qty} ta",
                callback_data="ignore"  # Bu tugma shunchaki ma'lumot uchun
            ),
            InlineKeyboardButton(
                text="➕",
                callback_data=CartCallback(action="plus", product_id=pid).pack()
            )
        )

    # Pastki umumiy tugmalar
    builder.row(InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="order"))
    builder.row(InlineKeyboardButton(text="🗑 Savatni tozalash", callback_data="clear_cart"))

    return builder.as_markup()


# 3. Menyu uchun tugmalar (har bir mahsulot ostida)
def get_product_keyboard(product_id, count=0):
    builder = InlineKeyboardBuilder()
    if count > 0:
        builder.add(InlineKeyboardButton(text=f"✅ Savatda ({count} ta)", callback_data=f"add_{product_id}"))
    else:
        builder.add(InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add_{product_id}"))
    return builder.as_markup()


# 4. Kontakt yuborish tugmasi
def get_contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# 5. To'lov turi tugmalari
def get_payment_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💵 Naqd", callback_data="pay_cash"))
    builder.row(InlineKeyboardButton(text="💳 Click / Payme", callback_data="pay_card"))
    return builder.as_markup()

# 6. Asosiy menyu tugmalari
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍔 Menyu")],
            [KeyboardButton(text="🗑 Savat"), KeyboardButton(text="👤 Profil")] # Profil ixtiyoriy
        ],
        resize_keyboard=True
    )

def get_categories_keyboard(categories):
    builder = InlineKeyboardBuilder()
    for category in categories:
        # Har bir kategoriya uchun alohida tugma
        builder.row(InlineKeyboardButton(text=category, callback_data=f"category_{category}"))
    return builder.as_markup()