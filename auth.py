from functools import wraps
from flask import abort, current_app
from flask_login import current_user

def role_required(*roles):
    """Decorator to require specific roles for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin role"""
    return role_required('admin')(f)

def store_manager_required(f):
    """Decorator to require store manager role"""
    return role_required('store_manager')(f)

def supplier_required(f):
    """Decorator to require supplier role"""
    return role_required('supplier')(f)
