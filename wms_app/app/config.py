import os
import json

basedir = os.path.abspath(os.path.dirname(__file__))
instance_folder_path = os.path.join(basedir, '..', 'instance')
settings_file_path = os.path.join(instance_folder_path, 'settings.json')

def load_settings():
    default_settings = {
        'HTTP_PORT': 5000,
        'AUTO_START_HTTP': True # This setting's effect is managed by run.py or deployment
    }
    if not os.path.exists(instance_folder_path):
        try:
            os.makedirs(instance_folder_path)
        except OSError as e:
            print(f"Warning: Could not create instance folder {instance_folder_path}. Using default settings. Error: {e}")
            return default_settings # Return defaults if instance folder can't be made

    if os.path.exists(settings_file_path):
        try:
            with open(settings_file_path, 'r') as f:
                loaded_settings = json.load(f)
                default_settings.update(loaded_settings)
        except (json.JSONDecodeError, TypeError):
            # Log error or handle if settings file is corrupt
            print(f"Warning: Could not decode {settings_file_path}. Using default settings.")
    return default_settings

# Load current settings for the Config class
current_settings = load_settings()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(instance_folder_path, 'app.db') # Corrected path
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    INSTANCE_FOLDER_PATH = instance_folder_path # Add this line

    # Apply loaded settings
    HTTP_PORT = current_settings.get('HTTP_PORT')
    AUTO_START_HTTP = current_settings.get('AUTO_START_HTTP')

def save_settings(settings_to_save):
    # Ensure instance folder exists
    if not os.path.exists(instance_folder_path):
        try:
            os.makedirs(instance_folder_path)
        except OSError as e:
            print(f"Error creating instance folder {instance_folder_path} during save: {e}")
            return False # Cannot save if instance folder can't be made

    try:
        with open(settings_file_path, 'w') as f:
            json.dump(settings_to_save, f, indent=4)
        # Update current_settings and app.config if app is running
        global current_settings
        current_settings.update(settings_to_save) # keep python module's current_settings in sync

        # Update Flask app's config if it's available (i.e., app has been created)
        # This makes changes immediate for some settings, though port usually needs restart.
        from flask import current_app
        if current_app:
             current_app.config['HTTP_PORT'] = current_settings.get('HTTP_PORT')
             current_app.config['AUTO_START_HTTP'] = current_settings.get('AUTO_START_HTTP')
        return True
    except Exception as e:
        print(f"Error saving settings to {settings_file_path}: {e}")
        return False
