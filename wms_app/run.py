from app import create_app, db
from app.models import Tray, Location, SampleRecord
import os # Added for path adjustment if needed, though not strictly used in final version

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Tray': Tray, 'Location': Location, 'SampleRecord': SampleRecord}

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("Running tests...")
        import unittest

        # Assuming this script (run.py) is in wms_app directory,
        # and 'tests' directory is a sibling to 'wms_app' (i.e., at project root)
        # For discovery to work correctly when run.py is in a subdirectory,
        # we might need to adjust path or ensure tests are run from project root.
        # If run from project root as `python wms_app/run.py test`, CWD is project root.
        # If run from wms_app as `python run.py test`, CWD is wms_app.

        # This typically works if 'tests' is in the CWD or PYTHONPATH
        # When running `python wms_app/run.py test` from project root, CWD is project root.
        loader = unittest.TestLoader()
        suite = loader.discover('tests')
        runner = unittest.TextTestRunner()
        result = runner.run(suite)
        if result.wasSuccessful():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        # AUTO_START_HTTP is more of a flag for deployment scripts.
        # The Flask dev server is started here if run.py is executed directly.
        port = app.config.get('HTTP_PORT', 5000) # Get port from app.config
        print(f"Starting WMS app on port {port}...")
        print(f"Configured AUTO_START_HTTP: {app.config.get('AUTO_START_HTTP')}")
        print(f"Note: To apply changes to HTTP_PORT, you may need to restart this script.")
        print(f"If using a production server (like Gunicorn), it will also need to be restarted with the new port.")

        app.run(host='0.0.0.0', port=port)
