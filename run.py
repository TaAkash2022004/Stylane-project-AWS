"""
Quick start script for StyleLane
"""
from app import app, db
from models import User, Store, Product, Sale, RestockRequest, Shipment

if __name__ == '__main__':
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if admin user exists, if not, initialize database
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Database not initialized. Please run: python init_db.py")
            print("Then restart the application.")
        else:
            print("StyleLane is ready!")
            print("\nAccess the application at: http://localhost:5000")
            print("\nDefault login credentials:")
            print("  Admin: admin / admin123")
            print("  Store Manager: storemanager1 / store123")
            print("  Supplier: supplier1 / supplier123")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
