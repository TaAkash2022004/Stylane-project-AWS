from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Store, Product, Sale, RestockRequest, Shipment
from auth import admin_required, store_manager_required, supplier_required
from datetime import datetime, timedelta
from sqlalchemy import func, and_

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stylane.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'products')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

db.init_app(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.template_filter('datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M'):
    """Format a datetime object."""
    if value is None:
        return ""
    return value.strftime(format)

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/')
def index():
    """Splash screen"""
    return render_template('splash.html')

@app.route('/home')
def home():
    """Home page - redirects based on user role"""
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'store_manager':
            return redirect(url_for('store_manager_dashboard'))
        elif current_user.role == 'supplier':
            return redirect(url_for('supplier_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    total_stores = Store.query.count()
    total_products = Product.query.count()
    total_users = User.query.count()
    pending_requests = RestockRequest.query.filter_by(status='pending').count()
    
    # Low stock products across all stores
    low_stock_products = Product.query.filter(
        Product.stock_quantity <= Product.low_stock_threshold
    ).all()
    
    # Recent sales summary
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(10).all()

    # Chart Data: Sales per Category
    sales_by_category = db.session.query(
        Product.category, 
        func.sum(Sale.total_amount)
    ).join(Sale).group_by(Product.category).all()
    
    category_labels = [item[0] or 'Uncategorized' for item in sales_by_category]
    category_data = [float(item[1]) for item in sales_by_category]
    
    # Chart Data: Sales Last 7 Days
    from datetime import timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    sales_last_7_days = db.session.query(
        func.date(Sale.sale_date),
        func.sum(Sale.total_amount)
    ).filter(Sale.sale_date >= seven_days_ago).group_by(func.date(Sale.sale_date)).all()
    
    # Fill in missing days
    sales_dates = []
    sales_values = []
    date_map = {item[0]: float(item[1]) for item in sales_last_7_days}
    
    for i in range(6, -1, -1):
        date = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
        sales_dates.append(date)
        sales_values.append(date_map.get(str(date), 0))
    
    return render_template('admin/dashboard.html',
                         total_stores=total_stores,
                         total_products=total_products,
                         total_users=total_users,
                         pending_requests=pending_requests,
                         low_stock_products=low_stock_products,
                         recent_sales=recent_sales,
                         category_labels=category_labels,
                         category_data=category_data,
                         sales_dates=sales_dates,
                         sales_values=sales_values)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Manage users"""
    users = User.query.all()
    stores = Store.query.all()
    return render_template('admin/users.html', users=users, stores=stores)

@app.route('/admin/users/create', methods=['POST'])
@login_required
@admin_required
def admin_create_user():
    """Create a new user"""
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    store_id = request.form.get('store_id') or None
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
        return redirect(url_for('admin_users'))
    
    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'error')
        return redirect(url_for('admin_users'))
    
    user = User(username=username, email=email, role=role)
    user.set_password(password)
    if store_id:
        user.store_id = int(store_id)
    
    db.session.add(user)
    db.session.commit()
    flash(f'User {username} created successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/update', methods=['POST'])
@login_required
@admin_required
def admin_update_user(user_id):
    """Update user"""
    user = User.query.get_or_404(user_id)
    user.email = request.form.get('email')
    user.role = request.form.get('role')
    user.store_id = request.form.get('store_id') or None
    user.is_active = request.form.get('is_active') == 'on'
    
    if request.form.get('password'):
        user.set_password(request.form.get('password'))
    
    db.session.commit()
    flash(f'User {user.username} updated successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/stores')
@login_required
@admin_required
def admin_stores():
    """Manage stores"""
    stores = Store.query.all()
    return render_template('admin/stores.html', stores=stores)

@app.route('/admin/stores/create', methods=['POST'])
@login_required
@admin_required
def admin_create_store():
    """Create a new store"""
    store = Store(
        name=request.form.get('name'),
        address=request.form.get('address'),
        phone=request.form.get('phone')
    )
    db.session.add(store)
    db.session.commit()
    flash(f'Store {store.name} created successfully.', 'success')
    return redirect(url_for('admin_stores'))

@app.route('/admin/stores/<int:store_id>/update', methods=['POST'])
@login_required
@admin_required
def admin_update_store(store_id):
    """Update store"""
    store = Store.query.get_or_404(store_id)
    store.name = request.form.get('name')
    store.address = request.form.get('address')
    store.phone = request.form.get('phone')
    db.session.commit()
    flash(f'Store {store.name} updated successfully.', 'success')
    return redirect(url_for('admin_stores'))

@app.route('/admin/inventory')
@login_required
@admin_required
def admin_inventory():
    """View all inventory across stores"""
    stores = Store.query.all()
    store_id = request.args.get('store_id', type=int)
    
    if store_id:
        products = Product.query.filter_by(store_id=store_id).all()
    else:
        products = Product.query.all()
    
    return render_template('admin/inventory.html', products=products, stores=stores, selected_store=store_id)

@app.route('/admin/reports')
@login_required
@admin_required
def admin_reports():
    """View reports"""
    # Sales summary by store
    sales_by_store = db.session.query(
        Store.name,
        func.sum(Sale.total_amount).label('total_sales'),
        func.count(Sale.id).label('transaction_count')
    ).join(Sale).group_by(Store.id).all()
    
    # Low stock summary
    low_stock_by_store = db.session.query(
        Store.name,
        func.count(Product.id).label('low_stock_count')
    ).join(Product).filter(
        Product.stock_quantity <= Product.low_stock_threshold
    ).group_by(Store.id).all()
    
    # Top selling products
    top_products = db.session.query(
        Product.name,
        Product.sku,
        func.sum(Sale.quantity).label('total_sold'),
        func.sum(Sale.total_amount).label('revenue')
    ).join(Sale).group_by(Product.id).order_by(
        func.sum(Sale.total_amount).desc()
    ).limit(10).all()
    
    return render_template('admin/reports.html',
                         sales_by_store=sales_by_store,
                         low_stock_by_store=low_stock_by_store,
                         top_products=top_products)

# ==================== STORE MANAGER ROUTES ====================

@app.route('/store-manager/dashboard')
@login_required
@store_manager_required
def store_manager_dashboard():
    """Store manager dashboard"""
    store = Store.query.get_or_404(current_user.store_id)
    products = Product.query.filter_by(store_id=store.id).all()
    low_stock_products = [p for p in products if p.is_low_stock]
    low_stock_count = len(low_stock_products)
    
    # Recent sales
    recent_sales = Sale.query.filter_by(store_id=store.id).order_by(
        Sale.sale_date.desc()
    ).limit(10).all()
    
    # Pending restock requests
    pending_requests = RestockRequest.query.filter_by(
        store_id=store.id,
        status='pending'
    ).count()
    
    return render_template('store_manager/dashboard.html',
                         store=store,
                         products=products,
                         low_stock_products=low_stock_products,
                         low_stock_count=low_stock_count,
                         recent_sales=recent_sales,
                         pending_requests=pending_requests)

@app.route('/store-manager/products')
@login_required
@store_manager_required
def store_manager_products():
    """View and manage products"""
    store = Store.query.get_or_404(current_user.store_id)
    products = Product.query.filter_by(store_id=store.id).all()
    return render_template('store_manager/products.html', products=products, store=store)

@app.route('/store-manager/products/create', methods=['POST'])
@login_required
@store_manager_required
def store_manager_create_product():
    """Create a new product"""
    store = Store.query.get_or_404(current_user.store_id)
    
    product = Product(
        name=request.form.get('name'),
        description=request.form.get('description'),
        category=request.form.get('category'),
        size=request.form.get('size'),
        color=request.form.get('color'),
        sku=request.form.get('sku'),
        price=float(request.form.get('price')),
        stock_quantity=int(request.form.get('stock_quantity', 0)),
        low_stock_threshold=int(request.form.get('low_stock_threshold', 10)),
        store_id=store.id
    )

    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Make filename unique
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            
            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image_filename = filename
    
    db.session.add(product)
    db.session.commit()
    flash(f'Product {product.name} added successfully.', 'success')
    return redirect(url_for('store_manager_products'))

@app.route('/store-manager/products/<int:product_id>/update', methods=['POST'])
@login_required
@store_manager_required
def store_manager_update_product(product_id):
    """Update product"""
    product = Product.query.get_or_404(product_id)
    
    if product.store_id != current_user.store_id:
        flash('You do not have permission to update this product.', 'error')
        return redirect(url_for('store_manager_products'))
    
    product.name = request.form.get('name')
    product.description = request.form.get('description')
    product.category = request.form.get('category')
    product.size = request.form.get('size')
    product.color = request.form.get('color')
    product.price = float(request.form.get('price'))
    product.stock_quantity = int(request.form.get('stock_quantity'))
    product.low_stock_threshold = int(request.form.get('low_stock_threshold'))
    product.updated_at = datetime.utcnow()

    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Make filename unique
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            
            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image_filename = filename
    
    db.session.commit()
    flash(f'Product {product.name} updated successfully.', 'success')
    return redirect(url_for('store_manager_products'))

@app.route('/store-manager/products/<int:product_id>/delete', methods=['POST'])
@login_required
@store_manager_required
def store_manager_delete_product(product_id):
    """Delete product"""
    product = Product.query.get_or_404(product_id)
    
    if product.store_id != current_user.store_id:
        flash('You do not have permission to delete this product.', 'error')
        return redirect(url_for('store_manager_products'))
    
    db.session.delete(product)
    db.session.commit()
    flash(f'Product {product.name} deleted successfully.', 'success')
    return redirect(url_for('store_manager_products'))

@app.route('/store-manager/sales')
@login_required
@store_manager_required
def store_manager_sales():
    """View and record sales"""
    store = Store.query.get_or_404(current_user.store_id)
    products = Product.query.filter_by(store_id=store.id).all()
    sales = Sale.query.filter_by(store_id=store.id).order_by(
        Sale.sale_date.desc()
    ).all()
    
    return render_template('store_manager/sales.html', products=products, sales=sales, store=store)

@app.route('/store-manager/sales/create', methods=['POST'])
@login_required
@store_manager_required
def store_manager_create_sale():
    """Record a new sale"""
    store = Store.query.get_or_404(current_user.store_id)
    product_id = int(request.form.get('product_id'))
    quantity = int(request.form.get('quantity'))
    
    product = Product.query.get_or_404(product_id)
    
    if product.store_id != store.id:
        flash('Invalid product for this store.', 'error')
        return redirect(url_for('store_manager_sales'))
    
    if product.stock_quantity < quantity:
        flash(f'Insufficient stock. Available: {product.stock_quantity}', 'error')
        return redirect(url_for('store_manager_sales'))
    
    # Create sale
    sale = Sale(
        product_id=product_id,
        store_id=store.id,
        quantity=quantity,
        unit_price=product.price,
        total_amount=product.price * quantity
    )
    
    # Update stock
    product.stock_quantity -= quantity
    product.updated_at = datetime.utcnow()
    
    db.session.add(sale)
    db.session.commit()
    
    flash(f'Sale recorded successfully. Total: ${sale.total_amount:.2f}', 'success')
    return redirect(url_for('store_manager_sales'))

@app.route('/store-manager/restock-requests')
@login_required
@store_manager_required
def store_manager_restock_requests():
    """View and create restock requests"""
    store = Store.query.get_or_404(current_user.store_id)
    products = Product.query.filter_by(store_id=store.id).all()
    requests = RestockRequest.query.filter_by(store_id=store.id).order_by(
        RestockRequest.created_at.desc()
    ).all()
    
    return render_template('store_manager/restock_requests.html',
                         products=products,
                         requests=requests,
                         store=store)

@app.route('/store-manager/restock-requests/create', methods=['POST'])
@login_required
@store_manager_required
def store_manager_create_restock_request():
    """Create a restock request"""
    store = Store.query.get_or_404(current_user.store_id)
    product_id = int(request.form.get('product_id'))
    quantity = int(request.form.get('quantity'))
    notes = request.form.get('notes', '')
    
    product = Product.query.get_or_404(product_id)
    
    if product.store_id != store.id:
        flash('Invalid product for this store.', 'error')
        return redirect(url_for('store_manager_restock_requests'))
    
    request_obj = RestockRequest(
        store_id=store.id,
        product_id=product_id,
        requested_quantity=quantity,
        requested_by=current_user.id,
        notes=notes
    )
    
    db.session.add(request_obj)
    db.session.commit()
    
    flash(f'Restock request created successfully.', 'success')
    return redirect(url_for('store_manager_restock_requests'))

@app.route('/store-manager/reports')
@login_required
@store_manager_required
def store_manager_reports():
    """View store reports"""
    store = Store.query.get_or_404(current_user.store_id)
    
    # Sales summary
    total_sales = db.session.query(func.sum(Sale.total_amount)).filter_by(
        store_id=store.id
    ).scalar() or 0
    
    total_transactions = Sale.query.filter_by(store_id=store.id).count()
    
    # Low stock products
    low_stock_products = Product.query.filter_by(store_id=store.id).filter(
        Product.stock_quantity <= Product.low_stock_threshold
    ).all()
    
    # Top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(Sale.quantity).label('total_sold'),
        func.sum(Sale.total_amount).label('revenue')
    ).join(Sale).filter(
        Product.store_id == store.id
    ).group_by(Product.id).order_by(
        func.sum(Sale.total_amount).desc()
    ).limit(10).all()
    
    return render_template('store_manager/reports.html',
                         store=store,
                         total_sales=total_sales,
                         total_transactions=total_transactions,
                         low_stock_products=low_stock_products,
                         top_products=top_products)

# ==================== SUPPLIER ROUTES ====================

@app.route('/supplier/dashboard')
@login_required
@supplier_required
def supplier_dashboard():
    """Supplier dashboard"""
    pending_requests = RestockRequest.query.filter_by(status='pending').count()
    approved_requests = RestockRequest.query.filter_by(status='approved', supplier_id=current_user.id).count()
    shipments = Shipment.query.filter_by(supplier_id=current_user.id).count()
    
    recent_requests = RestockRequest.query.filter_by(status='pending').order_by(
        RestockRequest.created_at.desc()
    ).limit(10).all()
    
    return render_template('supplier/dashboard.html',
                         pending_requests=pending_requests,
                         approved_requests=approved_requests,
                         shipments=shipments,
                         recent_requests=recent_requests)

@app.route('/supplier/restock-requests')
@login_required
@supplier_required
def supplier_restock_requests():
    """View and manage restock requests"""
    status_filter = request.args.get('status', 'all')
    
    query = RestockRequest.query
    
    if status_filter == 'pending':
        query = query.filter_by(status='pending')
    elif status_filter == 'approved':
        query = query.filter_by(status='approved', supplier_id=current_user.id)
    elif status_filter == 'rejected':
        query = query.filter_by(status='rejected', supplier_id=current_user.id)
    elif status_filter == 'shipped':
        query = query.filter_by(status='shipped', supplier_id=current_user.id)
    
    requests = query.order_by(RestockRequest.created_at.desc()).all()
    
    return render_template('supplier/restock_requests.html',
                         requests=requests,
                         status_filter=status_filter)

@app.route('/supplier/restock-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@supplier_required
def supplier_approve_request(request_id):
    """Approve a restock request"""
    request_obj = RestockRequest.query.get_or_404(request_id)
    
    if request_obj.status != 'pending':
        flash('This request has already been processed.', 'error')
        return redirect(url_for('supplier_restock_requests'))
    
    request_obj.status = 'approved'
    request_obj.supplier_id = current_user.id
    request_obj.updated_at = datetime.utcnow()
    
    # Create shipment
    shipment = Shipment(
        restock_request_id=request_obj.id,
        supplier_id=current_user.id,
        tracking_number=request.form.get('tracking_number', ''),
        expected_delivery_date=datetime.utcnow() + timedelta(days=7) if request.form.get('expected_delivery_date') else None,
        notes=request.form.get('notes', '')
    )
    
    db.session.add(shipment)
    db.session.commit()
    
    flash('Restock request approved and shipment created.', 'success')
    return redirect(url_for('supplier_restock_requests'))

@app.route('/supplier/restock-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@supplier_required
def supplier_reject_request(request_id):
    """Reject a restock request"""
    request_obj = RestockRequest.query.get_or_404(request_id)
    
    if request_obj.status != 'pending':
        flash('This request has already been processed.', 'error')
        return redirect(url_for('supplier_restock_requests'))
    
    request_obj.status = 'rejected'
    request_obj.supplier_id = current_user.id
    request_obj.notes = request.form.get('rejection_reason', '')
    request_obj.updated_at = datetime.utcnow()
    
    db.session.commit()
    flash('Restock request rejected.', 'info')
    return redirect(url_for('supplier_restock_requests'))

@app.route('/supplier/shipments')
@login_required
@supplier_required
def supplier_shipments():
    """View and manage shipments"""
    shipments = Shipment.query.filter_by(supplier_id=current_user.id).order_by(
        Shipment.created_at.desc()
    ).all()
    
    return render_template('supplier/shipments.html', shipments=shipments)

@app.route('/supplier/shipments/<int:shipment_id>/update-status', methods=['POST'])
@login_required
@supplier_required
def supplier_update_shipment_status(shipment_id):
    """Update shipment status"""
    shipment = Shipment.query.get_or_404(shipment_id)
    
    if shipment.supplier_id != current_user.id:
        flash('You do not have permission to update this shipment.', 'error')
        return redirect(url_for('supplier_shipments'))
    
    new_status = request.form.get('status')
    shipment.status = new_status
    
    if new_status == 'shipped' and not shipment.shipped_date:
        shipment.shipped_date = datetime.utcnow()
        # Update restock request status
        shipment.restock_request.status = 'shipped'
    
    if new_status == 'delivered' and not shipment.actual_delivery_date:
        shipment.actual_delivery_date = datetime.utcnow()
        # Update product stock
        product = shipment.restock_request.product
        product.stock_quantity += shipment.restock_request.requested_quantity
        product.updated_at = datetime.utcnow()
    
    shipment.tracking_number = request.form.get('tracking_number', shipment.tracking_number)
    shipment.notes = request.form.get('notes', shipment.notes)
    shipment.updated_at = datetime.utcnow()
    
    db.session.commit()
    flash('Shipment status updated successfully.', 'success')
    return redirect(url_for('supplier_shipments'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
