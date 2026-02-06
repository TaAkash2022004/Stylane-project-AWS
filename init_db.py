"""
Database initialization script with sample data
"""
from app import app, db
from models import User, Store, Product, Sale, RestockRequest, Shipment
from datetime import datetime, timedelta

def init_database():
    """Initialize database with sample data"""
    with app.app_context():
        # Drop all tables and recreate
        db.drop_all()
        db.create_all()
        
        print("Creating sample data...")
        
        # Create Admin user
        admin = User(
            username='admin',
            email='admin@stylane.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create Stores
        store1 = Store(
            name='StyleLane Downtown',
            address='123 Main Street, Downtown, NY 10001',
            phone='555-0101'
        )
        store2 = Store(
            name='StyleLane Uptown',
            address='456 Park Avenue, Uptown, NY 10002',
            phone='555-0102'
        )
        store3 = Store(
            name='StyleLane Mall',
            address='789 Shopping Center, Mall District, NY 10003',
            phone='555-0103'
        )
        db.session.add_all([store1, store2, store3])
        db.session.flush()
        
        # Create Store Managers
        store_manager1 = User(
            username='storemanager1',
            email='manager1@stylane.com',
            role='store_manager',
            store_id=store1.id
        )
        store_manager1.set_password('store123')
        
        store_manager2 = User(
            username='storemanager2',
            email='manager2@stylane.com',
            role='store_manager',
            store_id=store2.id
        )
        store_manager2.set_password('store123')
        
        store_manager3 = User(
            username='storemanager3',
            email='manager3@stylane.com',
            role='store_manager',
            store_id=store3.id
        )
        store_manager3.set_password('store123')
        
        db.session.add_all([store_manager1, store_manager2, store_manager3])
        
        # Create Suppliers
        supplier1 = User(
            username='supplier1',
            email='supplier1@fashion.com',
            role='supplier'
        )
        supplier1.set_password('supplier123')
        
        supplier2 = User(
            username='supplier2',
            email='supplier2@fashion.com',
            role='supplier'
        )
        supplier2.set_password('supplier123')
        
        db.session.add_all([supplier1, supplier2])
        db.session.flush()
        
        # Create Products for Store 1
        products_store1 = [
            Product(name='Classic White Shirt', description='Premium cotton shirt', category='Shirts', size='M', color='White', sku='SHIRT-WH-M-001', price=49.99, stock_quantity=25, low_stock_threshold=10, store_id=store1.id),
            Product(name='Classic White Shirt', description='Premium cotton shirt', category='Shirts', size='L', color='White', sku='SHIRT-WH-L-001', price=49.99, stock_quantity=15, low_stock_threshold=10, store_id=store1.id),
            Product(name='Denim Jeans', description='Classic blue denim', category='Pants', size='32', color='Blue', sku='JEAN-BL-32-001', price=79.99, stock_quantity=8, low_stock_threshold=10, store_id=store1.id),
            Product(name='Leather Jacket', description='Genuine leather jacket', category='Jackets', size='M', color='Black', sku='JACKET-BK-M-001', price=199.99, stock_quantity=5, low_stock_threshold=5, store_id=store1.id),
            Product(name='Running Shoes', description='Comfortable running shoes', category='Shoes', size='10', color='White', sku='SHOE-WH-10-001', price=89.99, stock_quantity=12, low_stock_threshold=10, store_id=store1.id),
        ]
        
        # Create Products for Store 2
        products_store2 = [
            Product(name='Classic White Shirt', description='Premium cotton shirt', category='Shirts', size='M', color='White', sku='SHIRT-WH-M-002', price=49.99, stock_quantity=20, low_stock_threshold=10, store_id=store2.id),
            Product(name='Slim Fit Chinos', description='Comfortable chino pants', category='Pants', size='34', color='Khaki', sku='CHINO-KH-34-001', price=69.99, stock_quantity=18, low_stock_threshold=10, store_id=store2.id),
            Product(name='Wool Sweater', description='Warm wool sweater', category='Sweaters', size='L', color='Navy', sku='SWEATER-NV-L-001', price=89.99, stock_quantity=7, low_stock_threshold=10, store_id=store2.id),
            Product(name='Sneakers', description='Casual sneakers', category='Shoes', size='9', color='Black', sku='SNEAKER-BK-9-001', price=79.99, stock_quantity=15, low_stock_threshold=10, store_id=store2.id),
        ]
        
        # Create Products for Store 3
        products_store3 = [
            Product(name='Polo Shirt', description='Classic polo shirt', category='Shirts', size='M', color='Blue', sku='POLO-BL-M-001', price=39.99, stock_quantity=22, low_stock_threshold=10, store_id=store3.id),
            Product(name='Cargo Pants', description='Durable cargo pants', category='Pants', size='36', color='Olive', sku='CARGO-OL-36-001', price=89.99, stock_quantity=6, low_stock_threshold=10, store_id=store3.id),
            Product(name='Hoodie', description='Comfortable hoodie', category='Sweaters', size='L', color='Gray', sku='HOODIE-GR-L-001', price=59.99, stock_quantity=11, low_stock_threshold=10, store_id=store3.id),
        ]
        
        db.session.add_all(products_store1 + products_store2 + products_store3)
        db.session.flush()
        
        # Create some sample sales
        sales = [
            Sale(product_id=products_store1[0].id, store_id=store1.id, quantity=2, unit_price=49.99, total_amount=99.98, sale_date=datetime.utcnow() - timedelta(days=1)),
            Sale(product_id=products_store1[2].id, store_id=store1.id, quantity=1, unit_price=79.99, total_amount=79.99, sale_date=datetime.utcnow() - timedelta(days=2)),
            Sale(product_id=products_store2[0].id, store_id=store2.id, quantity=3, unit_price=49.99, total_amount=149.97, sale_date=datetime.utcnow() - timedelta(hours=5)),
            Sale(product_id=products_store2[2].id, store_id=store2.id, quantity=1, unit_price=89.99, total_amount=89.99, sale_date=datetime.utcnow() - timedelta(days=3)),
            Sale(product_id=products_store3[0].id, store_id=store3.id, quantity=2, unit_price=39.99, total_amount=79.98, sale_date=datetime.utcnow() - timedelta(hours=10)),
        ]
        
        db.session.add_all(sales)
        db.session.flush()
        
        # Create some restock requests
        restock_request1 = RestockRequest(
            store_id=store1.id,
            product_id=products_store1[2].id,
            requested_quantity=20,
            status='pending',
            requested_by=store_manager1.id,
            notes='Running low on denim jeans'
        )
        
        restock_request2 = RestockRequest(
            store_id=store1.id,
            product_id=products_store1[3].id,
            requested_quantity=10,
            status='approved',
            supplier_id=supplier1.id,
            requested_by=store_manager1.id,
            notes='Need more leather jackets for winter season'
        )
        
        restock_request3 = RestockRequest(
            store_id=store3.id,
            product_id=products_store3[1].id,
            requested_quantity=15,
            status='pending',
            requested_by=store_manager3.id,
            notes='Cargo pants are popular this season'
        )
        
        db.session.add_all([restock_request1, restock_request2, restock_request3])
        db.session.flush()
        
        # Create a shipment for approved request
        shipment1 = Shipment(
            restock_request_id=restock_request2.id,
            supplier_id=supplier1.id,
            status='preparing',
            tracking_number='TRK123456789',
            expected_delivery_date=datetime.utcnow() + timedelta(days=7),
            notes='Preparing shipment'
        )
        
        db.session.add(shipment1)
        
        # Commit all changes
        db.session.commit()
        
        print("Database initialized successfully!")
        print("\nDefault login credentials:")
        print("  Admin: admin / admin123")
        print("  Store Manager 1: storemanager1 / store123")
        print("  Store Manager 2: storemanager2 / store123")
        print("  Store Manager 3: storemanager3 / store123")
        print("  Supplier 1: supplier1 / supplier123")
        print("  Supplier 2: supplier2 / supplier123")

if __name__ == '__main__':
    init_database()
