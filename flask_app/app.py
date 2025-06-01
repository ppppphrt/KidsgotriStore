from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from io import BytesIO
import os
from mimetypes import guess_type

app = Flask(__name__)
app.secret_key = 'loongwissawakorn'  # สำหรับ flash messages

# ข้อมูลสินค้า
products = {
    1: {
        "name": "KGT Black Shirt",
        "price": 550,
        "description": "KGT Black Shirt - ใส่แล้ววิ่งแรง",
        "image": "images/shirt1.jpg"
    },
    2: {
        "name": "KGT Bag",
        "price": 590,
        "description": "KGT Bag - ถือแล้วเท่ เหมาะกับทุกการแต่งตัว",
        "image": "images/dress1.jpg"
    },
    3: {
        "name": "Product3",
        "price": 999,
        "description": "Product3 - เดี๋ยวมาแน่ เตรียม F",
        "image": "images/jacket1.jpg"
    },
}

# SQLite Database config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'contact.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Contact model
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

# Order model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text, nullable=False)
    payment_slip = db.Column(db.LargeBinary, nullable=True)  # Store payment slip as BLOB
    payment_slip_filename = db.Column(db.String(200), nullable=True)  # Store original filename

# Admin model
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# สร้างฐานข้อมูลและ superuser
with app.app_context():
    try:
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            superuser = Admin(username='admin')
            superuser.set_password('rankaikhongloong')
            db.session.add(superuser)
            db.session.commit()
        print(f"Database created successfully at: {os.path.join(basedir, 'contact.db')}")
    except Exception as e:
        print(f"Error creating database: {e}")

@app.route('/')
def index():
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = products.get(product_id)
    return render_template('product_detail.html', product=product, product_id=product_id)

@app.route('/order/<int:product_id>', methods=['POST'])
def order_product(product_id):
    product = products.get(product_id)
    if not product:
        return "Product not found", 404

    customer_name = request.form['customer_name']
    address = request.form['address']
    phone = request.form['phone']
    payment_slip = request.files.get('payment_slip')

    # if not payment_slip:
    #     flash("กรุณาอัปโหลดสลิปการชำระเงิน", "danger")
    #     return redirect(url_for('product_detail', product_id=product_id))

    # Validate file extension
    allowed_extensions = {'jpg', 'jpeg', 'png'}
    if not '.' in payment_slip.filename or payment_slip.filename.lower().rsplit('.', 1)[1] not in allowed_extensions:
        flash("ไฟล์สลิปต้องเป็น JPG หรือ PNG เท่านั้น", "danger")
        return redirect(url_for('product_detail', product_id=product_id))

    payment_slip_data = payment_slip.read()
    payment_slip_filename = payment_slip.filename

    new_order = Order(
        customer_name=customer_name,
        product_name=product['name'],
        price=product['price'],
        phone=phone,
        address=address,
        payment_slip=payment_slip_data,
        payment_slip_filename=payment_slip_filename
    )

    try:
        db.session.add(new_order)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"เกิดข้อผิดพลาดในการบันทึกคำสั่งซื้อ: {str(e)}", "danger")
        return redirect(url_for('product_detail', product_id=product_id))

    flash("ขอบคุณสำหรับการสั่งซื้อ! ทางร้านจะติดต่อกลับภายใน 24 ชม.", "success")
    return redirect(url_for('thank_you', order_id=new_order.id))

@app.route('/thank_you/<int:order_id>')
def thank_you(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('thank_you.html', order=order)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']

        new_contact = Contact(name=name, email=email, subject=subject, message=message)
        try:
            db.session.add(new_contact)
            db.session.commit()
            flash('ส่งข้อความเรียบร้อยแล้ว!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"เกิดข้อผิดพลาดในการส่งข้อความ: {str(e)}", "danger")
        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')
    return render_template('admin_login.html')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    try:
        contacts = Contact.query.all()
        orders = Order.query.all()
        return render_template('admin_dashboard.html', contacts=contacts, orders=orders)
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {str(e)}", "danger")
        return redirect(url_for('admin_login'))

@app.route('/payment_slip/<int:order_id>')
@login_required
def view_payment_slip(order_id):
    order = Order.query.get_or_404(order_id)
    if not order.payment_slip:
        return "No payment slip available", 404
    mime_type, _ = guess_type(order.payment_slip_filename or 'image.jpg')
    return send_file(
        BytesIO(order.payment_slip),
        mimetype=mime_type,
        as_attachment=False,
        download_name=order.payment_slip_filename or f"payment_slip_{order_id}.jpg"

    )

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if Admin.query.filter_by(username=username).first():
            flash('มีผู้ใช้นี้อยู่แล้ว', 'warning')
        else:
            new_admin = Admin(username=username)
            new_admin.set_password(password)
            try:
                db.session.add(new_admin)
                db.session.commit()
                flash('เพิ่มผู้ดูแลระบบสำเร็จ', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f"เกิดข้อผิดพลาดในการเพิ่มผู้ดูแล: {str(e)}", "danger")
            return redirect(url_for('add_admin'))
    return render_template('add_admin.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('คุณได้ออกจากระบบแล้ว', 'info')
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)

# if __name__ == '__main__':
#     app.run(host="0.0.0.0", port=5000, debug=True)
