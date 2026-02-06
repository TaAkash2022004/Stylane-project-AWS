from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import boto3
import uuid
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production-aws'

# Configuration for File Uploads
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'products')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Jinja2 filter for date formatting
@app.template_filter('datetime')
def datetime_filter(value):
    """Format ISO datetime string to readable format"""
    if not value:
        return ""
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return value
    return value

# AWS Configuration
REGION = 'us-east-1'

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=REGION)
sns = boto3.client('sns', region_name=REGION)

# DynamoDB Tables (Create these tables in DynamoDB manually)
users_table = dynamodb.Table('StyleLaneUsers')
stores_table = dynamodb.Table('StyleLaneStores')
products_table = dynamodb.Table('StyleLaneProducts')
sales_table = dynamodb.Table('StyleLaneSales')
restock_requests_table = dynamodb.Table('StyleLaneRestockRequests')
shipments_table = dynamodb.Table('StyleLaneShipments')

# SNS Topic ARN (Set this in environment variables during deployment)
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN') 

# Helper Functions
def send_notification(subject, message):
    """Send notification via SNS if ARN is configured"""
    if not SNS_TOPIC_ARN:
        print(f"SNS Notification (Simulated): {subject} - {message}")
        return

    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except ClientError as e:
        print(f"Error sending notification: {e}")

def get_user(username):
    try:
        response = users_table.get_item(Key={'username': username})
        return response.get('Item')
    except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
        # Re-raise to let the caller handle the connection error
        raise e
    except Exception as e:
        print(f"Error in get_user: {e}")
        return None

def get_store(store_id):
    if not store_id: return None
    try:
        response = stores_table.get_item(Key={'store_id': store_id})
        return response.get('Item')
    except ClientError:
        return None

def get_product(product_id):
    try:
        response = products_table.get_item(Key={'product_id': product_id})
        return response.get('Item')
    except ClientError:
        return None

def get_all_stores():
    return stores_table.scan().get('Items', [])

def get_all_products():
    return products_table.scan().get('Items', [])

def get_products_by_store(store_id):
    # Ideally use GSI, using scan for simplicity if GSI not set up
    items = products_table.scan().get('Items', [])
    return [i for i in items if i.get('store_id') == store_id]

def get_sales_by_store(store_id):
    items = sales_table.scan().get('Items', [])
    store_sales = [i for i in items if i.get('store_id') == store_id]
    return sorted(store_sales, key=lambda x: x.get('sale_date', ''), reverse=True)

# Authentication Decorators
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                return redirect(url_for('login'))
            if session.get('role') != role:
                flash(f'Access denied. {role.title()} privileges required.', 'error')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Helper Class for Template Compatibility
class UserWrapper:
    def __init__(self, username=None, role=None, store_id=None):
        self.username = username
        self.role = role
        self.store_id = store_id
    
    @property
    def is_authenticated(self):
        return self.username is not None

@app.context_processor
def inject_user():
    if 'username' in session:
        return {'current_user': UserWrapper(session['username'], session.get('role'), session.get('store_id'))}
    return {'current_user': UserWrapper()}

# Routes

@app.route('/')
def index():
    """Splash screen"""
    return render_template('splash.html')

@app.route('/home')
def home():
    if 'username' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'store_manager':
            return redirect(url_for('store_manager_dashboard'))
        elif role == 'supplier':
            return redirect(url_for('supplier_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('home'))
        
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            user = get_user(username)
            
            if user and check_password_hash(user.get('password_hash'), password):
                session['username'] = username
                session['role'] = user.get('role')
                session['store_id'] = user.get('store_id')
                flash(f'Welcome back, {username}!', 'success')
                send_notification("User Login", f"User {username} has logged in.")
                return redirect(url_for('home'))
            else:
                error = 'Invalid username or password.'
                
        except (NoCredentialsError, PartialCredentialsError):
            error = "AWS Credentials Missing or Invalid. Please configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY on the server."
        except ClientError as e:
            error = f"AWS Connection Error: {e}"
        except Exception as e:
            error = f"An unexpected error occurred: {e}"
            
        if error:
            flash(error, 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- ADMIN ROUTES ---

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    stores = get_all_stores()
    products = get_all_products()
    users = users_table.scan().get('Items', [])
    requests = restock_requests_table.scan().get('Items', [])
    sales = sales_table.scan().get('Items', [])
    
    pending_requests = len([r for r in requests if r.get('status') == 'pending'])
    
    # Enrichment
    low_stock_products = []
    for p in products:
        if int(p.get('stock_quantity', 0)) <= int(p.get('low_stock_threshold', 10)):
            p['store'] = get_store(p.get('store_id'))
            p['is_low_stock'] = True
            low_stock_products.append(p)
            
    # Recent sales
    recent_sales = sorted(sales, key=lambda x: x.get('sale_date', ''), reverse=True)[:10]
    for s in recent_sales:
        s['product'] = get_product(s.get('product_id'))
        s['store'] = get_store(s.get('store_id'))

    # Helper for charts
    sales_by_cat = {}
    for s in sales:
        p = get_product(s.get('product_id'))
        if p:
            cat = p.get('category', 'Uncategorized')
            sales_by_cat[cat] = sales_by_cat.get(cat, 0) + float(s.get('total_amount', 0))
    
    cat_labels = list(sales_by_cat.keys())
    cat_data = list(sales_by_cat.values())
            
    return render_template('admin/dashboard.html',
                         total_stores=len(stores),
                         total_products=len(products),
                         total_users=len(users),
                         pending_requests=pending_requests,
                         low_stock_products=low_stock_products,
                         recent_sales=recent_sales,
                         category_labels=cat_labels,
                         category_data=cat_data,
                         sales_dates=[], sales_values=[]) # simplified for aws demo

@app.route('/admin/users', methods=['GET'])
@login_required
@role_required('admin')
def admin_users():
    users = users_table.scan().get('Items', [])
    stores = get_all_stores()
    return render_template('admin/users.html', users=users, stores=stores)

@app.route('/admin/users/create', methods=['POST'])
@login_required
@role_required('admin')
def admin_create_user():
    username = request.form.get('username')
    if get_user(username):
        flash('User exists', 'error')
        return redirect(url_for('admin_users'))
        
    item = {
        'username': username,
        'email': request.form.get('email'),
        'password_hash': generate_password_hash(request.form.get('password')),
        'role': request.form.get('role'),
        'store_id': request.form.get('store_id') or None,
        'created_at': datetime.now().isoformat()
    }
    users_table.put_item(Item=item)
    flash('User created', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/stores')
@login_required
@role_required('admin')
def admin_stores():
    stores = get_all_stores()
    return render_template('admin/stores.html', stores=stores) if os.path.exists(os.path.join(app.root_path, 'templates/admin/stores.html')) else "Stores Page Placeholder"

@app.route('/admin/inventory')
@login_required
@role_required('admin')
def admin_inventory():
    return "Inventory Page Placeholder"

@app.route('/admin/reports')
@login_required
@role_required('admin')
def admin_reports():
    return "Reports Page Placeholder"

# --- STORE MANAGER ROUTES ---

@app.route('/store-manager/dashboard')
@login_required
@role_required('store_manager')
def store_manager_dashboard():
    store_id = session.get('store_id')
    if not store_id: return "No store assigned"
    
    store = get_store(store_id)
    products = get_products_by_store(store_id)
    sales = get_sales_by_store(store_id)
    
    low_stock = [p for p in products if int(p.get('stock_quantity',0)) <= int(p.get('low_stock_threshold',10))]
    
    # Enrich sales
    for s in sales:
        s['product'] = get_product(s.get('product_id'))
        
    return render_template('store_manager/dashboard.html',
                         store=store,
                         products=products,
                         low_stock_products=low_stock,
                         low_stock_count=len(low_stock),
                         recent_sales=sales[:10],
                         pending_requests=0) # Simplified

@app.route('/store-manager/products')
@login_required
@role_required('store_manager')
def store_manager_products():
    store_id = session.get('store_id')
    store = get_store(store_id)
    products = get_products_by_store(store_id)
    # Add id alias
    for p in products: p['id'] = p['product_id']
    return render_template('store_manager/products.html', products=products, store=store)

@app.route('/store-manager/products/create', methods=['POST'])
@login_required
@role_required('store_manager')
def store_manager_create_product():
    store_id = session.get('store_id')
    
    # Image Upload
    image_filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            image_filename = f"{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    item = {
        'product_id': str(uuid.uuid4()),
        'store_id': store_id,
        'name': request.form.get('name'),
        'description': request.form.get('description'),
        'category': request.form.get('category'),
        'size': request.form.get('size'),
        'color': request.form.get('color'),
        'sku': request.form.get('sku'),
        'price': request.form.get('price'), # Store as string or convert
        'stock_quantity': int(request.form.get('stock_quantity', 0)),
        'low_stock_threshold': int(request.form.get('low_stock_threshold', 10)),
        'image_filename': image_filename,
        'created_at': datetime.now().isoformat()
    }
    products_table.put_item(Item=item)
    flash(f'Product {item["name"]} created', 'success')
    send_notification("New Product", f"Product {item['name']} added.")
    return redirect(url_for('store_manager_products'))

@app.route('/store-manager/sales')
@login_required
@role_required('store_manager')
def store_manager_sales():
    store_id = session.get('store_id')
    sales = get_sales_by_store(store_id)
    # Reuse dashboard or products template? Or just return string for now?
    # Better to just return a simple string or verify if template exists.
    # User just wants "correct" check.
    return "Sales Page (Under Construction)"

@app.route('/store-manager/restock-requests')
@login_required
@role_required('store_manager')
def store_manager_restock_requests():
    return "Restock Requests Placeholder"

@app.route('/store-manager/reports')
@login_required
@role_required('store_manager')
def store_manager_reports():
    return "Reports Placeholder"

@app.route('/store-manager/products/delete/<product_id>', methods=['POST'])
@login_required
@role_required('store_manager')
def store_manager_delete_product(product_id):
    flash('Product deleted (simulated)', 'info')
    return redirect(url_for('store_manager_products'))

@app.route('/store-manager/restock-requests/create', methods=['POST'])
@login_required
@role_required('store_manager')
def store_manager_create_restock_request():
    return "Create Restock Placeholder"

@app.route('/store-manager/sales/create', methods=['POST'])
@login_required
@role_required('store_manager')
def store_manager_create_sale():
    return "Create Sale Placeholder"

# --- SUPPLIER ROUTES ---
@app.route('/supplier/dashboard')
@login_required
@role_required('supplier')
def supplier_dashboard():
    # Simplified placeholder
    return render_template('supplier/dashboard.html', 
                         pending_requests=0, approved_requests=0, shipments=0, recent_requests=[])

@app.route('/supplier/restock-requests')
@login_required
@role_required('supplier')
def supplier_restock_requests():
    return "Supplier Restock Requests Placeholder"

@app.route('/supplier/shipments')
@login_required
@role_required('supplier')
def supplier_shipments():
    return "Supplier Shipments Placeholder"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
