import unittest
import tempfile
import os
from wms_app.app import create_app, db
from wms_app.app.models import Tray, Location, SampleRecord
from wms_app.app.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory SQLite for tests
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(tempfile.gettempdir(), 'test_app.db') # Or temp file
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False # Disable CSRF for forms if you have them in tests, not critical for API
    DEBUG = True # Ensure DEBUG is True for more error output if needed, or False to mimic prod

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        # If using temp file db:
        # if os.path.exists(os.path.join(tempfile.gettempdir(), 'test_app.db')):
        #     os.remove(os.path.join(tempfile.gettempdir(), 'test_app.db'))
        self.app_context.pop()

    # Helper methods (optional, can be added as needed)
    def create_tray(self, name="TestTray", location_count=5):
        return self.client.post('/api/trays', json={
            'name': name,
            'location_count': location_count
        })

    def place_sample(self, sample_id_str="S001", tray_id=1, location_id=None):
        payload = {'sample_id_str': sample_id_str, 'tray_id': tray_id}
        if location_id:
            payload['location_id'] = location_id
        return self.client.post('/api/samples/place', json=payload)

if __name__ == '__main__':
    unittest.main()
