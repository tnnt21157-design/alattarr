from flask import Flask, render_template, request, redirect, url_for, session, flash
from urllib.parse import quote as urllib_quote
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'attar_secret_key_change_in_production_2026')

_BASE = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(_BASE, 'alattar.db')
WHATSAPP_NUMBER = "962781611698"

# ==================== Database ====================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            icon TEXT DEFAULT '',
            description TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    # Default admin
    admin = c.execute('SELECT id FROM admin WHERE username = ?', ('YOUSEAF',)).fetchone()
    if not admin:
        pw_hash = generate_password_hash('0788522')
        c.execute('INSERT INTO admin (username, password_hash) VALUES (?, ?)', ('YOUSEAF', pw_hash))

    # Seed categories + products if empty
    if c.execute('SELECT COUNT(*) FROM categories').fetchone()[0] == 0:
        categories = [
            ('spices', 'البهارات والتوابل', '🌶️', 'جميع البهارات والخلطات وأسرار الطبخ', 1),
            ('herbs', 'الأعشاب الطبيعية', '🌿', 'قريص، بابونج، ميرمية، يانسون، شيح وأكثر', 2),
            ('oils', 'الزيوت الطبيعية', '🧴', 'زيت هيماني، زيت زيتون، جوز هند', 3),
            ('perfumes', 'العطور التركيب', '✨', 'أكثر من 120 نوع رجالي ونسائي وزيتي', 4),
            ('grains', 'البقوليات والحبوب', '🫘', 'فاصوليا، عدس، فريكة، برغل، حمص', 5),
            ('honey', 'العسل ومنتجات النحل', '🍯', 'عسل سدر، جبلي، حمضيات، غذاء ملكات', 6),
            ('vinegar', 'الخل الطبيعي', '🍏', 'خل التفاح الطبيعي الأصلي', 7),
            ('coffee', 'القهوة', '☕', 'قهوة إكسترا وقهوة عربية طازجة', 8),
        ]
        for key, title, icon, desc, order in categories:
            c.execute('INSERT INTO categories (key, title, icon, description, sort_order) VALUES (?, ?, ?, ?, ?)',
                      (key, title, icon, desc, order))

        # Get category ids
        cats = {row['key']: row['id'] for row in c.execute('SELECT id, key FROM categories').fetchall()}

        products = [
            # spices
            (cats['spices'], 'بهارات منسف أصلية', '4.50 د', 1),
            (cats['spices'], 'بهارات دجاج', '3.50 د', 2),
            (cats['spices'], 'بهارات شاورما', '4.00 د', 3),
            (cats['spices'], 'بهارات مندي', '4.00 د', 4),
            (cats['spices'], 'قرفة خشب', '5.00 د', 5),
            (cats['spices'], 'قرفة سيجار', '7.00 د', 6),
            (cats['spices'], 'زعتر بلدي', '3.00 د', 7),
            (cats['spices'], 'زعتر ورق', '6.00 د', 8),
            (cats['spices'], 'هيل مطحون فاخر', 'ابعث لمعرفة السعر', 9),
            (cats['spices'], 'فلفل أسود حب ومطحون', 'ابعث لمعرفة السعر', 10),
            (cats['spices'], 'كمون مطحون نقي', 'ابعث لمعرفة السعر', 11),
            (cats['spices'], 'كزبرة ناشفة', 'ابعث لمعرفة السعر', 12),
            (cats['spices'], 'كركم أصلي', 'ابعث لمعرفة السعر', 13),
            (cats['spices'], 'بابريكا حلوة وحارة', 'ابعث لمعرفة السعر', 14),
            (cats['spices'], 'بهارات برياني وحبة صينحة', 'ابعث لمعرفة السعر', 15),
            (cats['spices'], 'سماق بلدي حامض', 'ابعث لمعرفة السعر', 16),
            # herbs
            (cats['herbs'], 'ميرمية أردنية', '2.50 د', 1),
            (cats['herbs'], 'بابونج بلدي', '2.00 د', 2),
            (cats['herbs'], 'يانسون طبيعي', '2.00 د', 3),
            (cats['herbs'], 'نعناع ناشف', '1.50 د', 4),
            (cats['herbs'], 'كركديه أسواني', '3.00 د', 5),
            (cats['herbs'], 'شومر حب', '2.00 د', 6),
            (cats['herbs'], 'كمون حب', '2.00 د', 7),
            (cats['herbs'], 'قريص طبيعي', '2.50 د', 8),
            (cats['herbs'], 'شيح بري', '2.50 د', 9),
            (cats['herbs'], 'قيسوم جبلي', '3.00 د', 10),
            (cats['herbs'], 'زريعة البقدونس والكتان', 'ابعث لمعرفة السعر', 11),
            (cats['herbs'], 'مليسا واكليل الجبل (روزماري)', 'ابعث لمعرفة السعر', 12),
            (cats['herbs'], 'زعتر بري (زوفا)', '2.50 د', 13),
            # oils
            (cats['oils'], 'زيت زيتون بكر ممتاز (لتر)', '5.50 د', 1),
            (cats['oils'], 'زيت هيماني (حبة البركة 30 مل)', '3.00 د', 2),
            (cats['oils'], 'زيت هيماني (لوز حلو 30 مل)', '3.00 د', 3),
            (cats['oils'], 'زيت هيماني (خروع 30 مل)', '3.00 د', 4),
            (cats['oils'], 'زيت جوز الهند النقي', '4.50 د', 5),
            (cats['oils'], 'زيت السمسم البلدي', '4.00 د', 6),
            (cats['oils'], 'زيت الجرجير والصبار', 'ابعث لمعرفة السعر', 7),
            # perfumes
            (cats['perfumes'], 'عطور تركيب رجالية (120 نوع)', 'حسب نظام العروض', 1),
            (cats['perfumes'], 'عطور تركيب نسائية (ثبات عالي - 120 نوع)', 'حسب نظام العروض', 2),
            (cats['perfumes'], 'عطور زيتية مركزة بدون كحول', 'حسب نظام العروض', 3),
            (cats['perfumes'], 'توضيح: عطور تركيب وليست أصلية من الماركات', '-', 4),
            # grains
            (cats['grains'], 'فاصوليا بيضاء وحمراء', '1.25 د', 1),
            (cats['grains'], 'عدس حب وبجبه وأصفر', '1.50 د', 2),
            (cats['grains'], 'حمص حب بلدي', '1.80 د', 3),
            (cats['grains'], 'فريكة خضراء بلدي', '3.50 د', 4),
            (cats['grains'], 'برغل خشن وناعم', '1.40 د', 5),
            (cats['grains'], 'قمح القشطة', '1.20 د', 6),
            (cats['grains'], 'شوفان طبيعي', '2.00 د', 7),
            (cats['grains'], 'فول ناشف مدمس', '1.50 د', 8),
            # honey
            (cats['honey'], 'كيلو عسل طبيعي (مشكل)', '10.00 د', 1),
            (cats['honey'], 'عسل سدر طبيعي فاخر', 'ابعث لمعرفة السعر', 2),
            (cats['honey'], 'عسل جبلي بري', 'ابعث لمعرفة السعر', 3),
            (cats['honey'], 'عسل حمضيات صافي', 'ابعث لمعرفة السعر', 4),
            (cats['honey'], 'غذاء ملكات النحل الأصلي', 'ابعث لمعرفة السعر', 5),
            (cats['honey'], 'حبوب لقاح النحل', 'ابعث لمعرفة السعر', 6),
            (cats['honey'], 'عكبر سائل أو خام', 'ابعث لمعرفة السعر', 7),
            # vinegar
            (cats['vinegar'], 'خل تفاح طبيعي (نصف كيلو)', '2.00 د', 1),
            # coffee
            (cats['coffee'], 'قهوة إكسترا محمصة طازجة', '7.00 د', 1),
            (cats['coffee'], 'قهوة عربية مع هيل', '6.50 د', 2),
        ]
        for cat_id, name, price, order in products:
            c.execute('INSERT INTO products (category_id, name, price, sort_order) VALUES (?, ?, ?, ?)',
                      (cat_id, name, price, order))

        offers = [
            ('قنينة فئة 1 دينار', '1.00 د', 1),
            ('قنينة فئة 3 دنانير', '3.00 د', 2),
            ('قنينة فئة 5 دنانير', '5.00 د', 3),
            ('عرض خاص: 7 قناني فئة الدينار', '5.00 د', 4),
            ('عرض خاص: 3 قناني فئة 3 دنانير', '5.50 د', 5),
            ('عرض خاص: 3 قناني فئة 5 دنانير', '11.00 د', 6),
        ]
        for name, price, order in offers:
            c.execute('INSERT INTO offers (name, price, sort_order) VALUES (?, ?, ?)', (name, price, order))

    conn.commit()
    conn.close()

# Initialize on startup
init_db()

# ==================== Helpers ====================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def get_cart():
    return session.get('cart', {})

def cart_count():
    cart = get_cart()
    return sum(item['qty'] for item in cart.values())

def cart_total_display():
    """Simple display helper - not real calculation since prices are strings"""
    return cart_count()

@app.context_processor
def inject_globals():
    return {
        'cart_count': cart_count(),
        'whatsapp_number': WHATSAPP_NUMBER
    }

# ==================== Public Routes ====================

@app.route('/')
def index():
    conn = get_db()
    categories = conn.execute(
        'SELECT * FROM categories ORDER BY sort_order'
    ).fetchall()
    offers = conn.execute(
        'SELECT * FROM offers ORDER BY sort_order'
    ).fetchall()
    conn.close()
    return render_template('index.html', categories=categories, offers=offers)

@app.route('/category/<cat_key>')
def category(cat_key):
    conn = get_db()
    cat = conn.execute('SELECT * FROM categories WHERE key = ?', (cat_key,)).fetchone()
    if not cat:
        conn.close()
        return redirect(url_for('index'))
    products = conn.execute(
        'SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY sort_order',
        (cat['id'],)
    ).fetchall()
    conn.close()
    return render_template('category.html', cat=cat, products=products)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    name = request.form.get('name')
    price = request.form.get('price')
    qty = int(request.form.get('qty', 1))

    if not product_id or not name:
        return redirect(request.referrer or url_for('index'))

    cart = get_cart()
    if product_id in cart:
        cart[product_id]['qty'] += qty
    else:
        cart[product_id] = {'name': name, 'price': price, 'qty': qty}
    session['cart'] = cart
    flash(f'تمت إضافة "{name}" إلى السلة', 'success')
    return redirect(request.referrer or url_for('cart'))

@app.route('/update_cart', methods=['POST'])
def update_cart():
    cart = get_cart()
    product_id = request.form.get('product_id')
    action = request.form.get('action')

    if product_id in cart:
        if action == 'increase':
            cart[product_id]['qty'] += 1
        elif action == 'decrease':
            cart[product_id]['qty'] -= 1
            if cart[product_id]['qty'] <= 0:
                del cart[product_id]
        elif action == 'remove':
            del cart[product_id]
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    cart_items = get_cart()
    return render_template('cart.html', cart_items=cart_items)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart_items = get_cart()
    if not cart_items:
        flash('السلة فارغة', 'error')
        return redirect(url_for('cart'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()

        if not name or not phone:
            flash('الرجاء إدخال الاسم ورقم الهاتف', 'error')
            return render_template('checkout.html', cart_items=cart_items)

        message = f"🛒 *طلب جديد من موقع محمص وبن العطار*\n\n"
        message += f"👤 الاسم: {name}\n"
        message += f"📱 الهاتف: {phone}\n"
        message += f"📍 العنوان: {address}\n"
        if notes:
            message += f"📝 ملاحظات: {notes}\n"
        message += f"\n*المنتجات:*\n"
        for item in cart_items.values():
            message += f"• {item['name']} × {item['qty']} ({item['price']})\n"

        session.pop('cart', None)
        whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={urllib_quote(message)}"
        return render_template('checkout.html', success=True, whatsapp_url=whatsapp_url)

    return render_template('checkout.html', cart_items=cart_items, success=False)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# ==================== Admin ====================

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        admin = conn.execute('SELECT * FROM admin WHERE username = ?', (username,)).fetchone()
        conn.close()
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_logged'] = True
            session['admin_user'] = username
            return redirect(url_for('admin_dashboard'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    session.pop('admin_user', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    conn = get_db()
    stats = {
        'categories': conn.execute('SELECT COUNT(*) FROM categories').fetchone()[0],
        'products': conn.execute('SELECT COUNT(*) FROM products').fetchone()[0],
        'active_products': conn.execute('SELECT COUNT(*) FROM products WHERE is_active = 1').fetchone()[0],
        'offers': conn.execute('SELECT COUNT(*) FROM offers').fetchone()[0],
    }
    categories = conn.execute('SELECT * FROM categories ORDER BY sort_order').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', stats=stats, categories=categories)

@app.route('/admin/products')
@login_required
def admin_products():
    conn = get_db()
    cat_filter = request.args.get('cat')
    if cat_filter:
        products = conn.execute('''
            SELECT p.*, c.title as category_title, c.key as category_key
            FROM products p JOIN categories c ON p.category_id = c.id
            WHERE c.key = ?
            ORDER BY p.sort_order
        ''', (cat_filter,)).fetchall()
    else:
        products = conn.execute('''
            SELECT p.*, c.title as category_title, c.key as category_key
            FROM products p JOIN categories c ON p.category_id = c.id
            ORDER BY c.sort_order, p.sort_order
        ''').fetchall()
    categories = conn.execute('SELECT * FROM categories ORDER BY sort_order').fetchall()
    conn.close()
    return render_template('admin_products.html', products=products, categories=categories, current_cat=cat_filter)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@login_required
def admin_product_add():
    conn = get_db()
    categories = conn.execute('SELECT * FROM categories ORDER BY sort_order').fetchall()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '').strip()
        category_id = request.form.get('category_id')
        description = request.form.get('description', '').strip()
        is_active = 1 if request.form.get('is_active') else 0

        if name and price and category_id:
            max_order = conn.execute(
                'SELECT COALESCE(MAX(sort_order), 0) FROM products WHERE category_id = ?',
                (category_id,)
            ).fetchone()[0]
            conn.execute('''
                INSERT INTO products (category_id, name, price, description, is_active, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (category_id, name, price, description, is_active, max_order + 1))
            conn.commit()
            conn.close()
            flash('تمت إضافة المنتج بنجاح', 'success')
            return redirect(url_for('admin_products'))
        flash('الرجاء تعبئة الحقول المطلوبة', 'error')

    conn.close()
    return render_template('admin_product_form.html', categories=categories, product=None)

@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def admin_product_edit(product_id):
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    categories = conn.execute('SELECT * FROM categories ORDER BY sort_order').fetchall()

    if not product:
        conn.close()
        flash('المنتج غير موجود', 'error')
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '').strip()
        category_id = request.form.get('category_id')
        description = request.form.get('description', '').strip()
        is_active = 1 if request.form.get('is_active') else 0

        if name and price and category_id:
            conn.execute('''
                UPDATE products SET category_id=?, name=?, price=?, description=?, is_active=?
                WHERE id=?
            ''', (category_id, name, price, description, is_active, product_id))
            conn.commit()
            conn.close()
            flash('تم تحديث المنتج بنجاح', 'success')
            return redirect(url_for('admin_products'))
        flash('الرجاء تعبئة الحقول المطلوبة', 'error')

    conn.close()
    return render_template('admin_product_form.html', categories=categories, product=product)

@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
@login_required
def admin_product_delete(product_id):
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    flash('تم حذف المنتج', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/product/toggle/<int:product_id>', methods=['POST'])
@login_required
def admin_product_toggle(product_id):
    conn = get_db()
    product = conn.execute('SELECT is_active FROM products WHERE id = ?', (product_id,)).fetchone()
    if product:
        new_status = 0 if product['is_active'] else 1
        conn.execute('UPDATE products SET is_active = ? WHERE id = ?', (new_status, product_id))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_products'))

@app.route('/admin/offers')
@login_required
def admin_offers():
    conn = get_db()
    offers = conn.execute('SELECT * FROM offers ORDER BY sort_order').fetchall()
    conn.close()
    return render_template('admin_offers.html', offers=offers)

@app.route('/admin/offer/add', methods=['POST'])
@login_required
def admin_offer_add():
    name = request.form.get('name', '').strip()
    price = request.form.get('price', '').strip()
    if name and price:
        conn = get_db()
        max_order = conn.execute('SELECT COALESCE(MAX(sort_order), 0) FROM offers').fetchone()[0]
        conn.execute('INSERT INTO offers (name, price, sort_order) VALUES (?, ?, ?)', (name, price, max_order + 1))
        conn.commit()
        conn.close()
        flash('تمت إضافة العرض', 'success')
    return redirect(url_for('admin_offers'))

@app.route('/admin/offer/delete/<int:offer_id>', methods=['POST'])
@login_required
def admin_offer_delete(offer_id):
    conn = get_db()
    conn.execute('DELETE FROM offers WHERE id = ?', (offer_id,))
    conn.commit()
    conn.close()
    flash('تم حذف العرض', 'success')
    return redirect(url_for('admin_offers'))

# ==================== Run ====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
