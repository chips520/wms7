from flask import Blueprint, render_template, current_app

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/ui/trays')
def ui_trays():
    return render_template('trays.html', title="Tray Management")

@main_bp.route('/ui/locations/<int:tray_id>')
def ui_locations(tray_id):
    # We can pass tray_id to the template and fetch details via JS,
    # or fetch tray details here and pass to template.
    # For simplicity with dynamic JS, just pass tray_id.
    return render_template('locations.html', title="Location Management", tray_id=tray_id)

@main_bp.route('/ui/samples')
def ui_samples():
    return render_template('samples.html', title="Sample Management")

@main_bp.route('/ui/service')
def ui_service_management():
    # Pass current config to the template
    config = {
        'HTTP_PORT': current_app.config.get('HTTP_PORT'),
        'AUTO_START_HTTP': current_app.config.get('AUTO_START_HTTP')
    }
    return render_template('service.html', title="Service Management", config=config)
