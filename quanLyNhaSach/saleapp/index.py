import math
from functools import wraps
from itertools import product
from statistics import quantiles
import utils
from flask_admin import BaseView, expose
from saleapp import app, login, db
from flask import render_template, request, redirect, abort, session, jsonify, url_for
import dao
from flask_login import login_user, logout_user, current_user, login_required
from saleapp import admin
import cloudinary.uploader
from saleapp.models import *
import random
from saleapp.utils import count_cart


# Trang chu
@app.route('/')
def index():
    # Lấy thông tin người dùng từ session nếu đã đăng nhập
    user = None
    if 'user_id' in session:
        user = dao.get_user_by_id(
            session['user_id'])  # Hàm này phải được định nghĩa trong dao để lấy thông tin người dùng

    # Lấy tham số tìm kiếm và danh mục sản phẩm
    q = request.args.get("q")
    cate_id = request.args.get("category_id")
    page = request.args.get("page", 1)
    products = dao.load_products(q=q, cate_id=cate_id, page=int(page))


    # Truyền thông tin người dùng và sản phẩm vào template
    return render_template('index.html', products=products, user=user
                          )


@app.route('/stats')
def stats():
    total_revenue_value = utils.total_revenue_all()
    total_quantity = utils.total_quantity()
    return render_template('stats.html', total_revenue_all=total_revenue_value, total_quantity=total_quantity)


# Xem chi tiet san pham
@app.route('/products/<int:id>')
def details(id):
    products = db.session.query(Product, Author).join(Author, Product.author_id == Author.id).filter(
        Product.id == id).first()
    if products is None:
        abort(404)
    random_pages = random.randint(150, 500)
    return render_template('product-details.html', products=products, random_pages=random_pages)


@app.route('/api/books', methods=['GET'])
def get_books():
    books = Product.query.all()
    book_list = [{
        "id": book.id,
        "name": book.name,
        "category": book.category.name,
        "price": book.price
    } for book in books]
    return jsonify(book_list)


@app.route('/import_bill', methods=['POST'])
def import_bill():
    try:
        data = request.json
        customer_name = data.get("customerName")
        invoice_date = data.get("invoiceDate")
        staff_name = data.get("staffName")
        details = data.get("details")  # Dạng JSON chứa danh sách sách

        # Tạo một hóa đơn mới
        date_sale = datetime.now()
        new_bill = SaleBook(
            customer_name=customer_name,
            created_date=date_sale,
            staff_id=current_user.id  # Thay ID nhân viên xử lý hóa đơn tại đây
        )
        db.session.add(new_bill)
        db.session.flush()  # Đảm bảo `new_bill` có ID để dùng ở bước tiếp theo

        # Thêm chi tiết hóa đơn
        for detail in details:
            book = Product.query.get(detail.get("bookId"))
            if not book or book.quantity < int(detail.get("quantity")):
                return jsonify({"message": f"Sách {book.name if book else 'không xác định'} không đủ số lượng"}), 400

            book.quantity -= int(detail.get("quantity"))  # Cập nhật tồn kho
            db.session.add(book)

            bill_detail = SaleBookDetail(
                sale_book_id=new_bill.id,
                product_id=detail.get("bookId"),
                quantity=int(detail.get("quantity")),
                price=book.price
            )
            db.session.add(bill_detail)

        # Lưu thay đổi
        db.session.commit()

        return jsonify({"message": "Hóa đơn được lưu thành công!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Đã xảy ra lỗi: {str(e)}"}), 500


# Login
@app.route('/login', methods=['GET', 'POST'])
def login_my_user():
    err_msg = ""
    if current_user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        user = None
        if role == 'staff':
            role = Role.STAFF
            user = dao.auth_staff(username, password, role=role)
        elif role == 'admin':
            role = Role.ADMIN
            user = dao.auth_staff(username, password, role=role)
        elif role == 'manager':
            role = Role.MANAGER
            user = dao.auth_staff(username, password, role=role)
        else:
            role = Role.USER
            user = dao.auth_user(username, password, role=role)
        if user:
            login_user(user=user)
            session.modified = True

            return redirect(
                '/admin' if role in [Role.ADMIN, Role.MANAGER] else '/staff' if role in [Role.STAFF] else '/')
        else:
            err_msg = "*Tài khoản hoặc mật khẩu không đúng!"

    return render_template('login.html', err_msg=err_msg)


# Log.out
@app.route('/logout', methods=['post'])
def logout():
    logout_user()
    session.clear()
    return redirect('/')


# Đăng ký
@app.route('/register', methods=['get', 'post'])
def register():
    err_msg = None
    if request.method.__eq__('POST'):
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        if password.__eq__(confirm):
            username = request.form.get("username")
            name = request.form.get("name")
            avatar = request.files.get('avatar')
            avatar_path = None
            email = request.form.get('email')
            address = request.form.get('address')
            phone = request.form.get('phone')
            if avatar:
                res = cloudinary.uploader.upload(avatar)
                avatar_path = res['secure_url']
            dao.add_user(name=name, username=username, password=password, avatar=avatar_path, email=email,
                         address=address, phone=phone)
            return redirect('/login')
        else:
            err_msg = "Mật khẩu không khớp!"

    return render_template('register.html', err_msg=err_msg)


# Cập nhật giỏ hàng
@app.route('/api/add-cart', methods=['post'])
def add_to_cart():
    data = request.json
    id = str(data.get('id'))
    name = data.get('name')
    price = data.get('price')
    cart = session.get('cart')
    if not cart:
        cart = {}
    if id in cart:
        cart[id]['quantity'] = cart[id]['quantity'] + 1
    else:
        cart[id] = {'id': id, 'name': name, 'price': price, 'quantity': 1}
    session['cart'] = cart

    import utils
    return jsonify(utils.count_cart(cart))


# Xem giỏ hàng
@app.route('/cart')
def cart():
    return render_template('cart.html',
                           stats=utils.count_cart(session.get('cart')))


@app.route('/api/cart', methods=['GET'])
def get_cart():
    cart = session.get('cart', {})
    cart_items = [{
        'id': item['id'],
        'name': item['name'],
        'price': item['price'],
        'quantity': item['quantity']
    } for item in cart.values()]
    return jsonify(cart_items)


# Thanh Toán
@app.route("/api/pay", methods=['post', 'get'])
@login_required
def pay():
    if request.method.__eq__('POST'):
        data = request.get_json()
        cart = session.get('cart')
        customer_phone = data.get('customer_phone')
        customer_address = data.get('customer_address')
        payment_method = data.get('payment_method') == 'Online'  # Chuyển thành boolean
        delivery_method = data.get('delivery_method')
        dao.add_receipt(cart, customer_phone, customer_address, payment_method, delivery_method)
        return redirect('/')
    # try:
    #     dao.add_receipt(cart)
    # except Exception as ex:
    #     return jsonify({'status': 500, 'msg': str(ex)})
    # else:
    #     del session['cart']
    #     return jsonify({'status': 200, 'msg': 'successful'})
    return render_template('oder_book.html', user=current_user)


# Nhap thong tin đơn hàng
@app.route('/api/order', methods=['POST'])
def create_order():
    data = request.get_json()

    # Lấy thông tin từ người dùng
    user_id = current_user.id
    customer_phone = data.get('customer_phone')
    customer_address = data.get('customer_address')
    payment_method = data.get('payment_method') == 'Online'  # Chuyển thành boolean
    delivery_method = data.get('delivery_method')
    book_orders = data.get('book_orders')
    if not all([customer_phone, customer_address, delivery_method, book_orders]):
        return jsonify({"message": "Thông tin đặt hàng không đầy đủ!"}), 400

    # Danh sách chi tiết đơn hàng
    receipt_details = []

    for book_order in book_orders:
        book_id = book_order.get('book_id')
        quantity = book_order.get('quantity')

        if not book_id or not quantity:
            return jsonify({"message": "Thông tin sách không hợp lệ!"}), 400

        # Lấy thông tin sản phẩm
        book = Product.query.get(book_id)
        if not book:
            return jsonify({"message": f"Sách với ID {book_id} không tồn tại!"}), 400

        # Tạo đối tượng ReceiptDetail
        receipt_detail = ReceiptDetail(
            product_id=book.id,
            quantity=quantity,
            price=book.price
        )
        receipt_details.append(receipt_detail)

    # Tạo thời gian đặt hàng
    order_date = datetime.now()

    # Tạo đối tượng Receipt
    new_receipt = Receipt(
        customer_phone=customer_phone,
        customer_address=customer_address,
        payment_method=payment_method,
        delivery_method=delivery_method,
        customer_id=user_id,
        create_date=order_date,
        receipt_details=receipt_details
    )

    # Lưu vào cơ sở dữ liệu
    try:
        db.session.add(new_receipt)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Đã xảy ra lỗi: {str(e)}"}), 500

    session['cart'] = {}

    return jsonify({"message": "Đặt sách thành công!"}), 200
    return redirect(url_for('/'), user=current_user)



# Update số lượng sản phẩm trong giỏ hàng
@app.route('/api/update-cart', methods=['put'])
def update_cart():
    data = request.json
    id = str(data.get('id'))
    quantity = data.get('quantity')
    cart = session.get('cart')
    if cart and id in cart:
        cart[id]['quantity'] = quantity
        session['cart'] = cart
    return jsonify(utils.count_cart(cart))


# Xóa sản phẩm trong giỏ hàng
@app.route('/api/delete-cart/<product_id>', methods=['delete'])
def delete_cart(product_id):
    cart = session.get('cart')
    if cart and product_id in cart:
        del cart[product_id]
        session['cart'] = cart

    return jsonify(utils.count_cart(cart))


@app.context_processor
def common_attributes():
    return {
        "categories": dao.load_categories()
    }


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


@app.context_processor
def comment_respone():
    return {
        "cart_stats": utils.count_cart(session.get('cart'))
    }



@app.route('/staff', methods=['GET', 'POST'])
def staff():
    return render_template('staff.html')



if __name__ == "__main__":
    with app.app_context():
        app.run(debug=True)
