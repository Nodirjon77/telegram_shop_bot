import sqlite3


def connect_db():
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row
    return conn


def create_db():
    conn = connect_db()
    cursor = conn.cursor()

    # 1. Foydalanuvchilar jadvali (Reklama va baza uchun)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT
        )
    ''')

    # 2. Mahsulotlar jadvali (Kategoriya ustuni bilan)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            photo TEXT,
            category TEXT DEFAULT 'Boshqa',
            quantity INTEGER DEFAULT 0 
        )
    ''')

    # 3. Savat jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            UNIQUE(user_id, product_id)
        )
    ''')

    conn.commit()
    conn.close()

def get_categories():
    """Mavjud barcha takrorlanmas kategoriyalarni olish"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = [row['category'] for row in cursor.fetchall()]
    conn.close()
    return categories


def get_products_by_category(category_name):
    """Tanlangan kategoriya bo'yicha mahsulotlarni olish"""
    conn = connect_db()
    # MANA SHU QATOR QO'SHILDI: Baza endi ma'lumotlarni nomlari bilan beradi
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE category = ?", (category_name,))

    # Qaytayotgan ma'lumotlarni to'liq lug'atga (dict) o'giramiz
    products = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return products

# --- ADMIN UCHUN FUNKSIYALAR ---
def add_product(name, price, photo, category, quantity):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, price, photo, category, quantity) VALUES (?, ?, ?, ?, ?)',
                   (name, price, photo, category, quantity))
    conn.commit()
    conn.close()


def get_all_products():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return products


# --- FOYDALANUVCHI (SAVAT) UCHUN FUNKSIYALAR ---
def add_to_cart(user_id, product_id):
    conn = connect_db()
    cursor = conn.cursor()
    # Agar mahsulot bo'lsa sonini +1 qiladi, bo'lmasa yangi qo'shadi
    cursor.execute('''
        INSERT INTO cart (user_id, product_id, quantity) 
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, product_id) 
        DO UPDATE SET quantity = quantity + 1
    ''', (user_id, product_id))
    conn.commit()
    conn.close()

def update_cart_quantity(user_id, product_id, delta):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE cart SET quantity = quantity + ? 
        WHERE user_id = ? AND product_id = ?
    ''', (delta, user_id, product_id))

    # Agar soni 0 yoki undan kam bo'lib qolsa, o'chirib yuboramiz
    cursor.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ? AND quantity <= 0",
                   (user_id, product_id))
    conn.commit()
    conn.close()


def delete_cart_item(user_id, product_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    conn.commit()
    conn.close()


def get_cart_products(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    query = """
    SELECT p.id, p.name, p.price, c.quantity
    FROM cart c
    JOIN products p ON c.product_id = p.id
    WHERE c.user_id = ?
    """
    cursor.execute(query, (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items


def get_product_count(user_id, product_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?",
                   (user_id, product_id))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


def clear_cart(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def delete_product_from_db(product_id):
    conn = connect_db()
    cursor = conn.cursor()

    # 1. Avval savatdan o'chiramiz (Xatolik bo'lmasligi uchun)
    cursor.execute("DELETE FROM cart WHERE product_id = ?", (product_id,))

    # 2. Keyin mahsulotlar jadvalidan o'chiramiz
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))

    conn.commit()
    conn.close()

def add_user(telegram_id, full_name, username):
    conn = connect_db()
    cursor = conn.cursor()
    # INSERT OR IGNORE - agar bu foydalanuvchi bazada bo'lsa, qayta yozmaydi (xato bermaydi)
    cursor.execute('''
        INSERT OR IGNORE INTO users (telegram_id, full_name, username) 
        VALUES (?, ?, ?)
    ''', (telegram_id, full_name, username))
    conn.commit()
    conn.close()

def get_all_users():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [user['telegram_id'] for user in users]


# Ombordan sotib olingan mahsulot sonini ayirib tashlash
def reduce_product_quantity(product_id, amount):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()

    # Bazadagi quantity ni olingan amount ga kamaytiramiz
    cursor.execute('''
        UPDATE products 
        SET quantity = quantity - ? 
        WHERE id = ?
    ''', (amount, product_id))

    conn.commit()
    conn.close()


# Mijozning savatidagi narsalarni ombordan ayirish uchun tortib olish
def get_cart_items(user_id):
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row  # Ustun nomlari bilan ishlash uchun
    cursor = conn.cursor()

    # "cart" degan joyga o'zingizning savat jadvallingiz nomini yozing
    # (masalan cart, yoki basket, yoki user_cart)
    cursor.execute('''
        SELECT product_id, quantity 
        FROM cart 
        WHERE user_id = ?
    ''', (user_id,))

    items = cursor.fetchall()
    conn.close()
    return items


# Mahsulotning ombordagi qoldig'ini (zaxirasini) bilish
def get_product_quantity(product_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM products WHERE id = ?", (product_id,))
    result = cursor.fetchone()
    conn.close()

    # Agar mahsulot topilsa zaxirasini, topilmasa 0 qaytaradi
    return result[0] if result else 0

# Admin barcha mahsulotlarni ko'rishi uchun
def get_all_products_admin():
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, quantity FROM products")
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return products

# Tanlangan mahsulotning ombordagi sonini yangilash
def update_product_quantity(product_id, new_quantity):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_quantity, product_id))
    conn.commit()
    conn.close()