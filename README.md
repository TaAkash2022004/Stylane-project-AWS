# StyleLane: Scalable Inventory Management and Reporting System

A comprehensive inventory management system for fashion retailers with multi-store support, role-based access control, and restocking coordination.

## Features

- **Multi-Store Inventory Management**: Track inventory across multiple fashion retail stores
- **Role-Based Access Control**: Three distinct roles (Admin, Store Manager, Supplier)
- **Stock Tracking**: Monitor stock levels with automatic low-stock alerts
- **Restocking System**: Coordinate restocking requests between stores and suppliers
- **Sales Tracking**: Record and track sales data
- **Reporting**: Generate inventory and sales reports

## System Roles

### Admin
- Manage Store Manager and Supplier accounts
- View inventory across all stores
- Access overall stock and sales reports
- Monitor low-stock alerts system-wide
- Manage user roles and permissions

### Store Manager
- Add and update products for their store
- Track sales
- Request restocks when stock is low
- View store-specific inventory and reports
- Receive low-stock notifications

### Supplier
- View restock requests from store managers
- Accept or reject restock requests
- Update shipment status
- Notify store managers when products are shipped
- Maintain product availability records

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize the database:
```bash
python init_db.py
```

3. Run the application:
```bash
python app.py
```
   Or use the quick start script:
```bash
python run.py
```

4. Access the application at `http://localhost:5000`

## Default Login Credentials

- **Admin**: username: `admin`, password: `admin123`
- **Store Manager**: username: `storemanager1`, password: `store123`
- **Supplier**: username: `supplier1`, password: `supplier123`

## Project Structure

```
stylane-aws/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── auth.py                # Authentication utilities
├── init_db.py             # Database initialization script
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── admin/
│   ├── store_manager/
│   └── supplier/
├── static/                # Static files
│   ├── css/
│   └── js/
└── instance/              # SQLite database (created on first run)
```

## Database Schema

- **users**: User accounts with roles
- **stores**: Store information
- **products**: Product inventory
- **restock_requests**: Restocking requests from stores
- **shipments**: Shipment tracking

## Future Enhancements

- AWS integration for cloud deployment
- Real-time notifications
- Advanced analytics and reporting
- Mobile app support
- API endpoints for external integrations
