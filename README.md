# WMS 料位管理服务应用 (WMS Material Location Management Service)

This application provides a service for managing material locations on trays, typically for use with AGVs or similar systems. It includes an HTTP API and a basic web UI.

## Features

*   Tray Management: Create, list, update, delete trays. Each tray has a configurable number of locations.
*   Location Management: Enable/disable specific locations, view location status.
*   Sample Management: Place samples into locations (automatically finding empty spots or using specified ones), query sample locations, clear samples from locations.
*   Configurable HTTP service (port, auto-start option).
*   Data stored in an SQLite database (`instance/app.db`).
*   Settings stored in `instance/settings.json`.

## Project Structure

*   `run.py`: Main script to start the application.
*   `wms_app/`: Main application package.
    *   `app/`: Contains the Flask app core.
        *   `__init__.py`: Application factory.
        *   `config.py`: Configuration loading (default and from `instance/settings.json`).
        *   `models.py`: SQLAlchemy database models.
        *   `routes.py`: API endpoint definitions.
        *   `main_routes.py`: UI page route definitions.
        *   `templates/`: HTML templates for the UI.
    *   `instance/`:
        *   `app.db`: SQLite database file (created automatically).
        *   `settings.json`: Application settings (HTTP port, auto-start flag - created/updated via UI or API).
*   `venv/`: Python virtual environment (if created as per setup).
*   `require.md`: Original requirements document.

## Setup

1.  **Clone the repository (if applicable).**
2.  **Create a Python virtual environment:**
    ```bash
    python -m venv venv
    ```
3.  **Activate the virtual environment:**
    *   Windows: `venv\Scripts\activate`
    *   macOS/Linux: `source venv/bin/activate`
4.  **Install dependencies:**
    ```bash
    pip install Flask Flask-SQLAlchemy SQLAlchemy
    ```
    (These should be the main ones based on the project progress so far. If other dependencies were added, list them here.)

## Running the Application Manually

1.  **Ensure your virtual environment is activated.**
2.  **Run the application:**
    ```bash
    python run.py
    ```
3.  The application will start an HTTP server. By default, it listens on `http://0.0.0.0:5000`.
    The port can be configured via the UI (Service Management page) or by editing `instance/settings.json` (changes require an application restart).
4.  Access the UI by navigating to `http://localhost:<port>/` in your web browser (e.g., `http://localhost:5000/`).
5.  API endpoints are available under the `/api` prefix (e.g., `http://localhost:5000/api/trays`).

## Application Auto-Start on System Boot

The `AUTO_START_HTTP` setting (configurable in the UI or `instance/settings.json`) is a flag that can be used by a system service manager. Setting it to `true` indicates the intention for the service to start automatically. The application itself doesn't implement system-level auto-start; you need to configure it using your operating system's tools.

### Linux (using `systemd`)

1.  **Create a service file:**
    Create a file named `wms-app.service` in `/etc/systemd/system/`:
    ```ini
    [Unit]
    Description=WMS Material Location Management Service
    After=network.target

    [Service]
    User=<your_user>  # Replace with the user you want to run the app as
    Group=<your_group> # Replace with the group for the user
    WorkingDirectory=/path/to/your/wms_app # Replace with the actual absolute path to the wms_app directory (containing run.py)
    Environment="PATH=/path/to/your/wms_app/venv/bin" # Absolute path to venv's bin
    ExecStart=/path/to/your/wms_app/venv/bin/python run.py
    Restart=always
    # StandardOutput=append:/var/log/wms-app/output.log # Optional: configure logging
    # StandardError=append:/var/log/wms-app/error.log  # Optional: configure logging

    [Install]
    WantedBy=multi-user.target
    ```
    *   **Important:**
        *   Replace `<your_user>`, `<your_group>`, and `/path/to/your/wms_app` with appropriate values. The path must be absolute.
        *   Ensure `run.py` and the Python interpreter in the `venv` are executable by this user.
        *   The `AUTO_START_HTTP` setting in `settings.json` doesn't directly control systemd. Systemd will start it regardless if the service is enabled. You could add a condition to `ExecStartPre` in the systemd unit to check this flag if you want systemd to respect it, for example, by having a small script that reads the JSON and exits with failure if auto-start is false.

2.  **Reload systemd daemon:**
    ```bash
    sudo systemctl daemon-reload
    ```
3.  **Enable the service (to start on boot):**
    ```bash
    sudo systemctl enable wms-app.service
    ```
4.  **Start the service immediately:**
    ```bash
    sudo systemctl start wms-app.service
    ```
5.  **Check status:**
    ```bash
    sudo systemctl status wms-app.service
    ```

### Windows (using Task Scheduler)

1.  **Open Task Scheduler.**
2.  **Click "Create Basic Task..."**
    *   **Name:** `WMS Application`
    *   **Trigger:** Select "When the computer starts".
    *   **Action:** Select "Start a program".
    *   **Program/script:** Enter the full path to the `python.exe` in your virtual environment (e.g., `C:\path\to\your\wms_app\venv\Scripts\python.exe`).
    *   **Add arguments (optional):** Enter `run.py`.
    *   **Start in (optional):** Enter the full path to your `wms_app` directory (e.g., `C:\path\to\your\wms_app`). This is important so `run.py` can find other files.
3.  **Finish the wizard.**
4.  **Modify task for robustness (optional but recommended):**
    *   Open the properties of the created task.
    *   Under the "General" tab, you might want to set "Run whether user is logged on or not" and "Run with highest privileges".
    *   Under the "Settings" tab, configure "If the task fails, restart every..."
    *   Similar to systemd, the `AUTO_START_HTTP` flag is not directly used by Task Scheduler. The task will run if enabled.

## Logging

Basic application events (like sample placement, clearing) should be logged. Currently, this is planned but not yet fully implemented in detail (placeholder TODOs in code). Production deployments should configure more robust logging (e.g., to files, especially when run as a background service).

## Future Considerations / TODOs (from requirements)

*   Detailed application logging for all key operations.
*   More robust error handling and user feedback in the UI.
*   Potentially more flexible location position identifiers.
*   Refined handling of "stopping" the service from the UI (likely means signaling a process manager or just for config).
