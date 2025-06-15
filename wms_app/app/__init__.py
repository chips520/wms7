import logging
from logging.handlers import RotatingFileHandler
import os
from flask import Flask
from .config import Config
from .models import db
# We will add migrate later if needed, for now direct SQLAlchemy
# from flask_migrate import Migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # Import and register blueprints here to avoid circular imports
    from .routes import api_bp # Correct place for import relative to app context
    app.register_blueprint(api_bp)

    from .main_routes import main_bp # Import the new blueprint
    app.register_blueprint(main_bp) # Register it

    if not app.debug and not app.testing: # Don't use file logging for debug/test
        instance_path = app.config.get('INSTANCE_FOLDER_PATH', os.path.join(os.path.dirname(__file__), '..', 'instance'))
        if not os.path.exists(instance_path):
            try:
                os.makedirs(instance_path)
            except OSError: # Handle potential race condition or permission issue
                app.logger.error(f"Could not create instance folder at {instance_path} for logging.")

        if os.path.exists(instance_path): # Proceed only if instance path exists or was created
            log_file = os.path.join(instance_path, 'app.log')

            file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

            app.logger.setLevel(logging.INFO)
            app.logger.info('WMS Application startup')

    with app.app_context():
        db.create_all()

    return app
