import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Set dummy AWS credentials to avoid NoCredentialsError during import
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

try:
    import app_aws
except ImportError:
    # If app_aws is not found, maybe we need to add current dir to path
    sys.path.append(os.getcwd())
    import app_aws

from werkzeug.security import generate_password_hash

class TestAppAws(unittest.TestCase):
    def setUp(self):
        self.app = app_aws.app.test_client()
        self.app.testing = True
        app_aws.app.config['PROPAGATE_EXCEPTIONS'] = True
        
        # Mock DynamoDB Tables attached to the module
        self.users_table_mock = MagicMock()
        app_aws.users_table = self.users_table_mock
        
        self.stores_table_mock = MagicMock()
        app_aws.stores_table = self.stores_table_mock
        
        self.products_table_mock = MagicMock()
        app_aws.products_table = self.products_table_mock
        
        self.sales_table_mock = MagicMock()
        app_aws.sales_table = self.sales_table_mock

        self.restock_requests_table_mock = MagicMock()
        app_aws.restock_requests_table = self.restock_requests_table_mock

        self.shipments_table_mock = MagicMock()
        app_aws.shipments_table = self.shipments_table_mock
        
        # Mock SNS client
        self.sns_mock = MagicMock()
        app_aws.sns = self.sns_mock
        
        # Set SNS ARN for testing
        app_aws.SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:123456789012:TestTopic'

    def tearDown(self):
        # Clean up session
        with self.app.session_transaction() as sess:
            sess.clear()

    def test_splash_screen(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        # Check for some text likely in splash.html. 
        # Since I can't see splash.html content directly here without reading it, 
        # I'll just check status 200 which confirms the route works.

    def test_login_page_load(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_login_failure(self):
        # Setup mock to return no user (empty dict or None)
        self.users_table_mock.get_item.return_value = {} # DynamoDB get_item returns empty dict if not found usually, or 'Item' key is missing
        
        response = self.app.post('/login', data={
            'username': 'nonexistent',
            'password': 'password'
        }, follow_redirects=True)
        
        self.assertIn(b'Invalid username or password', response.data)

    def test_login_success(self):
        # Setup mock user
        username = 'validuser'
        password = 'validpass'
        pw_hash = generate_password_hash(password)
        
        user_data = {
            'username': username,
            'password_hash': pw_hash,
            'role': 'store_manager',
            'store_id': 'store_123'
        }
        
        # DynamoDB get_item returns 'Item' key if found
        self.users_table_mock.get_item.return_value = {'Item': user_data}
        
        response = self.app.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
        
        # Check redirect to home or welcome message
        self.assertIn(f'Welcome back, {username}!'.encode(), response.data)
        
        # Check SNS was called
        self.sns_mock.publish.assert_called()

    def test_access_denied_role(self):
        # Login as store_manager
        with self.app.session_transaction() as sess:
            sess['username'] = 'manager'
            sess['role'] = 'store_manager'
            sess['store_id'] = '1'
            
        # Try to access admin dashboard
        response = self.app.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Access denied', response.data)

    def test_store_manager_create_product(self):
        # Login as store_manager
        with self.app.session_transaction() as sess:
            sess['username'] = 'manager'
            sess['role'] = 'store_manager'
            sess['store_id'] = 'store_123'
            
        # Mock dependencies
        file_storage = (b'fake image data', 'test.jpg')
        
        data = {
            'name': 'Test Product',
            'description': 'A test product',
            'category': 'T-Shirts',
            'size': 'M',
            'color': 'Blue',
            'sku': 'TP-001',
            'price': '25.00',
            'stock_quantity': '100',
            'low_stock_threshold': '10',
            # 'image': file_storage # Handling file upload mocking is complex, skip for now or use simplified
        }
        
        # We need to mock os.path.exists or make sure UPLOAD FOLDER exists effectively
        # app_aws.py creates it on import: os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        # So it should be fine.
        
        response = self.app.post('/store-manager/products/create', data=data, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.products_table_mock.put_item.assert_called()
        self.sns_mock.publish.assert_called() # Notification for new product

if __name__ == '__main__':
    unittest.main()
