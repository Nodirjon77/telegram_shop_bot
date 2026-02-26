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
            category TEXT DEFAULT 'Boshqa'
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
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE category = ?", (category_name,))
    products = cursor.fetchall()
    conn.close()
    return products

# --- ADMIN UCHUN FUNKSIYALAR ---
def add_product(name, price, photo, category):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, price, photo, category) VALUES (?, ?, ?, ?)',
                   (name, price, photo, category))
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