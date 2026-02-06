from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model with role-based access"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'store_manager', 'supplier'
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True)  # For store managers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    store = db.relationship('Store', backref='managers', lazy=True)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class Store(db.Model):
    """Store model"""
    __tablename__ = 'stores'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='store', lazy=True, cascade='all, delete-orphan')
    restock_requests = db.relationship('RestockRequest', backref='store', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Store {self.name}>'

class Product(db.Model):
    """Product model"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # e.g., 'Shirts', 'Pants', 'Shoes', etc.
    size = db.Column(db.String(20))  # e.g., 'S', 'M', 'L', 'XL', etc.
    color = db.Column(db.String(30))
    sku = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=10, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True) # New field for product image
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='product', lazy=True, cascade='all, delete-orphan')
    
    @property
    def is_low_stock(self):
        """Check if product is low in stock"""
        return self.stock_quantity <= self.low_stock_threshold
    
    @property
    def stock_status(self):
        """Get stock status string"""
        if self.stock_quantity == 0:
            return 'Out of Stock'
        elif self.is_low_stock:
            return 'Low Stock'
        else:
            return 'In Stock'
    
    def __repr__(self):
        return f'<Product {self.name} (Store: {self.store_id})>'

class Sale(db.Model):
    """Sale model for tracking sales"""
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    store = db.relationship('Store', backref='sales', lazy=True)
    
    def __repr__(self):
        return f'<Sale {self.id} - Product {self.product_id}>'

class RestockRequest(db.Model):
    """Restock request model"""
    __tablename__ = 'restock_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    requested_quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'approved', 'rejected', 'shipped'
    supplier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Relationships
    product = db.relationship('Product', backref='restock_requests', lazy=True)
    supplier = db.relationship('User', foreign_keys=[supplier_id], backref='restock_requests', lazy=True)
    requester = db.relationship('User', foreign_keys=[requested_by], backref='requests_made', lazy=True)
    shipment = db.relationship('Shipment', backref='restock_request', uselist=False, lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<RestockRequest {self.id} - Status: {self.status}>'

class Shipment(db.Model):
    """Shipment model for tracking deliveries"""
    __tablename__ = 'shipments'
    
    id = db.Column(db.Integer, primary_key=True)
    restock_request_id = db.Column(db.Integer, db.ForeignKey('restock_requests.id'), nullable=False, unique=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='preparing', nullable=False)  # 'preparing', 'shipped', 'delivered', 'cancelled'
    tracking_number = db.Column(db.String(100))
    shipped_date = db.Column(db.DateTime, nullable=True)
    expected_delivery_date = db.Column(db.DateTime, nullable=True)
    actual_delivery_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Relationships
    supplier = db.relationship('User', backref='shipments', lazy=True)
    
    def __repr__(self):
        return f'<Shipment {self.id} - Status: {self.status}>'
