from flask import Blueprint, request, jsonify, current_app
from .models import db, Tray, Location, SampleRecord # Added SampleRecord just in case for future use in this file
from sqlalchemy.exc import IntegrityError
from datetime import datetime # Ensure datetime is imported
from .config import save_settings, current_settings as app_current_settings # For settings API

# Using a Blueprint for better organization
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/trays', methods=['POST'])
def create_tray():
    data = request.get_json()
    if not data or not 'name' in data or not 'location_count' in data:
        return jsonify({'error': 'Missing name or location_count in request body'}), 400

    name = data['name']
    location_count = data['location_count']

    if not isinstance(location_count, int) or location_count <= 0:
        return jsonify({'error': 'location_count must be a positive integer'}), 400

    if Tray.query.filter_by(name=name).first():
        return jsonify({'error': f'Tray with name "{name}" already exists'}), 409 # Conflict

    try:
        tray = Tray(name=name, location_count=location_count)
        db.session.add(tray)
        db.session.flush() # To get tray.id for locations

        locations_to_add = []
        for i in range(1, location_count + 1):
            # Default position identifier, can be made more flexible later
            position_id = f'Pos{i}'
            location = Location(tray_id=tray.id, position_identifier=position_id)
            locations_to_add.append(location)

        db.session.bulk_save_objects(locations_to_add)
        db.session.commit()
        current_app.logger.info(f"Tray '{tray.name}' (ID: {tray.id}) created with {location_count} locations.")
        return jsonify({
            'id': tray.id,
            'name': tray.name,
            'location_count': tray.location_count,
            'message': f'Tray "{name}" created with {location_count} locations.'
        }), 201
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"IntegrityError while creating tray '{name}': {str(e)}")
        # Check if it's the unique constraint for tray name
        if 'UNIQUE constraint failed: tray.name' in str(e.orig):
             return jsonify({'error': f'Tray with name "{name}" already exists.'}), 409
        return jsonify({'error': 'Database integrity error.', 'details': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exception while creating tray '{name}': {str(e)}")
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)}), 500

@api_bp.route('/trays', methods=['GET'])
def get_trays():
    trays = Tray.query.all()
    return jsonify([{
        'id': tray.id,
        'name': tray.name,
        'location_count': tray.location_count
    } for tray in trays]), 200

@api_bp.route('/trays/<int:tray_id>', methods=['GET'])
def get_tray(tray_id):
    tray = db.session.get(Tray, tray_id) # Using db.session.get for primary key lookup
    if not tray:
        return jsonify({'error': 'Tray not found'}), 404

    locations = Location.query.filter_by(tray_id=tray.id).all()
    return jsonify({
        'id': tray.id,
        'name': tray.name,
        'location_count': tray.location_count,
        'locations': [{
            'id': loc.id,
            'position_identifier': loc.position_identifier,
            'is_enabled': loc.is_enabled,
            'sample_id_str': loc.sample_record.sample_id_str if loc.sample_record else None
        } for loc in locations]
    }), 200

@api_bp.route('/trays/<int:tray_id>', methods=['PUT'])
def update_tray(tray_id):
    tray = db.session.get(Tray, tray_id) # Using db.session.get
    if not tray:
        return jsonify({'error': 'Tray not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided for update'}), 400

    if 'name' in data:
        new_name = data['name']
        if Tray.query.filter(Tray.id != tray_id, Tray.name == new_name).first():
             return jsonify({'error': f'Another tray with name "{new_name}" already exists'}), 409
        tray.name = new_name

    if 'location_count' in data and data['location_count'] != tray.location_count:
         return jsonify({'error': 'Modifying location_count is not supported. Please delete and recreate the tray if different capacity is needed.'}), 400

    try:
        db.session.commit()
        return jsonify({'id': tray.id, 'name': tray.name, 'location_count': tray.location_count, 'message': 'Tray updated successfully'}), 200
    except IntegrityError as e:
        db.session.rollback()
        if 'UNIQUE constraint failed: tray.name' in str(e.orig):
             return jsonify({'error': f'Tray name "{tray.name}" already exists.'}), 409
        return jsonify({'error': 'Database integrity error during update.', 'details': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An unexpected error occurred during update', 'details': str(e)}), 500

@api_bp.route('/trays/<int:tray_id>', methods=['DELETE'])
def delete_tray(tray_id):
    tray = db.session.get(Tray, tray_id) # Using db.session.get
    if not tray:
        return jsonify({'error': 'Tray not found'}), 404
    try:
        # Associated locations and potentially sample records (if cascade is set up from location to sample record if a sample is only on one location)
        # will be handled by SQLAlchemy's cascade options defined in models.
        # Specifically, Tray->Location is cascade="all, delete-orphan".
        # If a SampleRecord is tied to a Location, ensure that relationship is handled (e.g. set location.sample_record_id to null or delete SampleRecord if appropriate)
        # Current model: Location.sample_record is a relationship, clearing sample_record_id from Location is the main action.
        # If SampleRecord needs to be deleted when a Tray is deleted, that logic needs to be explicit if not covered by cascades.
        # For now, deleting a tray deletes its locations. If those locations held samples, the SampleRecord entries themselves are NOT deleted by this action alone,
        # but they become "orphaned" in the sense they are not in a location anymore. This might be desired or might need adjustment.
        # Let's assume for now that SampleRecords are independent entities unless explicitly deleted.

        # To ensure samples in the locations of the tray being deleted are disassociated:
        locations_to_clear = Location.query.filter_by(tray_id=tray.id).all()
        for loc in locations_to_clear:
            loc.sample_record_id = None
            loc.sample_record = None
        db.session.flush() # Apply these changes before deleting the tray

        db.session.delete(tray)
        db.session.commit()
        current_app.logger.info(f"Tray ID {tray_id} ('{tray.name}') and its locations deleted.")
        return jsonify({'message': f'Tray ID {tray_id} ("{tray.name}") and its locations deleted successfully. Any samples previously in these locations are now unassigned.'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exception while deleting tray ID {tray_id}: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred during deletion', 'details': str(e)}), 500

# --- Location Endpoints ---

@api_bp.route('/trays/<int:tray_id>/locations', methods=['GET'])
def get_tray_locations(tray_id):
    tray = db.session.get(Tray, tray_id)
    if not tray:
        return jsonify({'error': 'Tray not found'}), 404

    locations = Location.query.filter_by(tray_id=tray.id).order_by(Location.id).all()
    return jsonify([{
        'id': loc.id,
        'position_identifier': loc.position_identifier,
        'is_enabled': loc.is_enabled,
        'tray_id': loc.tray_id,
        'sample_id_str': loc.sample_record.sample_id_str if loc.sample_record else None,
        'sample_record_id': loc.sample_record_id
    } for loc in locations]), 200

@api_bp.route('/locations/<int:location_id>/enable', methods=['PUT'])
def enable_location(location_id):
    location = db.session.get(Location, location_id)
    if not location:
        return jsonify({'error': 'Location not found'}), 404

    if location.is_enabled:
        return jsonify({'message': 'Location is already enabled'}), 200 # Or 304 Not Modified

    location.is_enabled = True
    try:
        db.session.commit()
        current_app.logger.info(f"Location ID {location_id} enabled.")
        return jsonify({
            'id': location.id,
            'position_identifier': location.position_identifier,
            'is_enabled': location.is_enabled,
            'message': 'Location enabled successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exception while enabling location ID {location_id}: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)}), 500

@api_bp.route('/locations/<int:location_id>/disable', methods=['PUT'])
def disable_location(location_id):
    location = db.session.get(Location, location_id)
    if not location:
        return jsonify({'error': 'Location not found'}), 404

    if not location.is_enabled:
        return jsonify({'message': 'Location is already disabled'}), 200 # Or 304 Not Modified

    # Optional: Check if location is occupied before disabling
    if location.sample_record_id:
        current_app.logger.warning(f"Attempt to disable occupied Location ID {location_id} denied.")
        return jsonify({'error': 'Cannot disable occupied location. Clear sample first.'}), 400

    location.is_enabled = False
    try:
        db.session.commit()
        current_app.logger.info(f"Location ID {location_id} disabled.")
        return jsonify({
            'id': location.id,
            'position_identifier': location.position_identifier,
            'is_enabled': location.is_enabled,
            'message': 'Location disabled successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exception while disabling location ID {location_id}: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)}), 500

@api_bp.route('/trays/<int:tray_id>/empty_location', methods=['GET'])
def get_empty_location(tray_id):
    tray = db.session.get(Tray, tray_id)
    if not tray:
        return jsonify({'error': 'Tray not found'}), 404

    # Find the first location that is enabled and has no sample_record_id
    empty_location = Location.query.filter_by(
        tray_id=tray_id,
        is_enabled=True,
        sample_record_id=None
    ).order_by(Location.id).first() # Order by ID or position_identifier for predictability

    if not empty_location:
        return jsonify({'error': 'No empty and enabled location found on this tray'}), 404

    return jsonify({
        'id': empty_location.id,
        'position_identifier': empty_location.position_identifier,
        'tray_id': empty_location.tray_id
    }), 200

# --- Sample Placement and Querying Endpoints ---

@api_bp.route('/samples/place', methods=['POST'])
def place_sample():
    data = request.get_json()
    if not data or not data.get('sample_id_str') or not data.get('tray_id'):
        return jsonify({'error': 'Missing sample_id_str or tray_id in request body'}), 400

    sample_id_str = data['sample_id_str']
    tray_id = data['tray_id']
    target_location_id = data.get('location_id') # Optional: user specifies location

    # Check if sample_id_str already exists anywhere
    existing_sample_record = SampleRecord.query.filter_by(sample_id_str=sample_id_str).first()
    if existing_sample_record:
        existing_location = Location.query.filter_by(sample_record_id=existing_sample_record.id).first()
        if existing_location:
            current_app.logger.warning(f"Attempt to place existing Sample ID '{sample_id_str}'. Rejected. Already at Tray ID {existing_location.tray_id}, Location ID {existing_location.id}.")
            return jsonify({
                'error': f'Sample ID "{sample_id_str}" already exists at Tray ID {existing_location.tray_id}, Location ID {existing_location.id} (Position: {existing_location.position_identifier})'
            }), 409 # Conflict
        else:
            # This case (SampleRecord exists but not linked to a Location) should ideally not happen with current logic.
            current_app.logger.warning(f"Attempt to place existing Sample ID '{sample_id_str}' which has no location. Data integrity issue?.")
             return jsonify({'error': f'Sample ID "{sample_id_str}" already exists but is not assigned to a location. Please check data integrity.'}), 409


    tray = db.session.get(Tray, tray_id)
    if not tray:
        return jsonify({'error': f'Tray ID {tray_id} not found'}), 404

    chosen_location = None
    if target_location_id:
        location_to_check = db.session.get(Location, target_location_id)
        if not location_to_check or location_to_check.tray_id != tray_id:
            return jsonify({'error': f'Location ID {target_location_id} not found on Tray ID {tray_id}'}), 404
        if not location_to_check.is_enabled:
            return jsonify({'error': f'Location ID {target_location_id} (Position: {location_to_check.position_identifier}) is disabled'}), 400
        if location_to_check.sample_record_id:
            return jsonify({'error': f'Location ID {target_location_id} (Position: {location_to_check.position_identifier}) is already occupied'}), 400
        chosen_location = location_to_check
    else:
        # Find an empty, enabled location
        empty_location = Location.query.filter_by(
            tray_id=tray_id,
            is_enabled=True,
            sample_record_id=None
        ).order_by(Location.id).first()
        if not empty_location:
            current_app.logger.warning(f"No empty location found on Tray ID {tray_id} for sample '{sample_id_str}'.")
            return jsonify({'error': f'No empty and enabled location found on Tray ID {tray_id}'}), 404
        chosen_location = empty_location

    try:
        new_sample_record = SampleRecord(sample_id_str=sample_id_str, timestamp=datetime.utcnow())
        db.session.add(new_sample_record)
        db.session.flush() # To get new_sample_record.id

        chosen_location.sample_record_id = new_sample_record.id
        chosen_location.sample_record = new_sample_record

        db.session.commit()
        current_app.logger.info(f"Sample '{new_sample_record.sample_id_str}' placed in Tray ID {chosen_location.tray_id}, Location ID {chosen_location.id}.")
        return jsonify({
            'message': 'Sample placed successfully',
            'sample_id_str': new_sample_record.sample_id_str,
            'tray_id': chosen_location.tray_id,
            'location_id': chosen_location.id,
            'position_identifier': chosen_location.position_identifier,
            'timestamp': new_sample_record.timestamp.isoformat()
        }), 201
    except IntegrityError as e: # Catch potential race condition if sample_id_str becomes non-unique
        db.session.rollback()
        current_app.logger.error(f"IntegrityError during placement of sample '{sample_id_str}': {str(e)}")
        if 'UNIQUE constraint failed: sample_record.sample_id_str' in str(e.orig):
             return jsonify({'error': f'Sample ID "{sample_id_str}" was created by another request. Please try again or check the sample.'}), 409
        return jsonify({'error': 'Database integrity error during sample placement.', 'details': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exception during placement of sample '{sample_id_str}': {str(e)}")
        return jsonify({'error': 'An unexpected error occurred during sample placement', 'details': str(e)}), 500

@api_bp.route('/samples/<path:sample_id_str>', methods=['GET']) # Using path for potentially complex sample IDs
def get_sample_location(sample_id_str):
    sample_record = SampleRecord.query.filter_by(sample_id_str=sample_id_str).first()
    if not sample_record:
        return jsonify({'error': f'Sample ID "{sample_id_str}" not found'}), 404

    location = Location.query.filter_by(sample_record_id=sample_record.id).first()
    if not location:
        # This state (sample record exists but not linked to a location) should ideally be prevented.
        return jsonify({'error': f'Sample ID "{sample_id_str}" found but not assigned to any location. Data inconsistency.'}), 500

    return jsonify({
        'sample_id_str': sample_record.sample_id_str,
        'tray_id': location.tray_id,
        'tray_name': location.tray.name, # Added for convenience
        'location_id': location.id,
        'position_identifier': location.position_identifier,
        'timestamp': sample_record.timestamp.isoformat()
    }), 200

@api_bp.route('/locations/<int:location_id>/clear', methods=['DELETE']) # Changed from POST to DELETE for semantic correctness
def clear_location(location_id):
    location = db.session.get(Location, location_id)
    if not location:
        return jsonify({'error': 'Location not found'}), 404

    if not location.sample_record_id:
        return jsonify({'message': 'Location is already empty'}), 200

    sample_record_to_delete_id = location.sample_record_id
    try:
        location.sample_record_id = None
        location.sample_record = None

        # Now delete the SampleRecord itself, as it's no longer in a location
        sample_record_to_delete = db.session.get(SampleRecord, sample_record_to_delete_id)
        if sample_record_to_delete:
            db.session.delete(sample_record_to_delete)

        db.session.commit()
        current_app.logger.info(f"Sample cleared from Location ID {location_id}. SampleRecord ID {sample_record_to_delete_id} deleted.")
        return jsonify({'message': f'Sample cleared from Location ID {location_id} (Position: {location.position_identifier}) and sample record deleted.'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exception while clearing Location ID {location_id}: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred while clearing location', 'details': str(e)}), 500

@api_bp.route('/trays/<int:tray_id>/clear_all', methods=['POST']) # Kept as POST as it's a bulk action
def clear_all_locations_on_tray(tray_id):
    tray = db.session.get(Tray, tray_id)
    if not tray:
        return jsonify({'error': 'Tray not found'}), 404

    locations_on_tray = Location.query.filter_by(tray_id=tray.id).all()
    if not any(loc.sample_record_id for loc in locations_on_tray):
        return jsonify({'message': f'All locations on Tray ID {tray_id} are already empty.'}), 200

    sample_records_to_delete_ids = []
    cleared_locations_count = 0
    try:
        for loc in locations_on_tray:
            if loc.sample_record_id:
                sample_records_to_delete_ids.append(loc.sample_record_id)
                loc.sample_record_id = None
                loc.sample_record = None
                cleared_locations_count +=1

        if sample_records_to_delete_ids:
            # Bulk delete SampleRecords
            # This might be slow for very large numbers, consider batching or direct SQL delete in such cases
            SampleRecord.query.filter(SampleRecord.id.in_(sample_records_to_delete_ids)).delete(synchronize_session=False)

        db.session.commit()
        current_app.logger.info(f"Cleared {cleared_locations_count} sample(s) from Tray ID {tray_id}.")
        return jsonify({'message': f'Successfully cleared {cleared_locations_count} sample(s) from Tray ID {tray_id} and deleted their records.'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exception while clearing all locations on Tray ID {tray_id}: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred while clearing all locations on tray', 'details': str(e)}), 500

# --- Settings API Endpoints ---

@api_bp.route('/settings', methods=['GET'])
def get_settings():
    # Return current_settings which are loaded from file or defaults
    # Ensure we are sending the values that are currently in effect or will be on next start
    settings_to_show = {
        'HTTP_PORT': current_app.config.get('HTTP_PORT'),
        'AUTO_START_HTTP': current_app.config.get('AUTO_START_HTTP')
    }
    return jsonify(settings_to_show), 200

@api_bp.route('/settings', methods=['PUT'])
def update_settings():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    new_settings = {}
    if 'HTTP_PORT' in data:
        try:
            new_settings['HTTP_PORT'] = int(data['HTTP_PORT'])
            if not (1024 <= new_settings['HTTP_PORT'] <= 65535):
                err_msg = "Port must be between 1024 and 65535"
                current_app.logger.warning(f"Invalid settings update: HTTP_PORT {data['HTTP_PORT']}. Error: {err_msg}")
                raise ValueError(err_msg)
        except ValueError as e:
            # Logged above if it's our custom error, else log other ValueErrors
            if not "Port must be between" in str(e):
                 current_app.logger.warning(f"Invalid settings update: HTTP_PORT {data.get('HTTP_PORT')}. Error: {str(e)}")
            return jsonify({'error': f'Invalid HTTP_PORT: {str(e)}'}), 400

    if 'AUTO_START_HTTP' in data:
        if not isinstance(data['AUTO_START_HTTP'], bool):
            err_msg = "AUTO_START_HTTP must be a boolean"
            current_app.logger.warning(f"Invalid settings update: AUTO_START_HTTP {data['AUTO_START_HTTP']}. Error: {err_msg}")
            return jsonify({'error': err_msg}), 400
        new_settings['AUTO_START_HTTP'] = data['AUTO_START_HTTP']

    if not new_settings:
         current_app.logger.warning(f"No valid settings provided for update. Data received: {data}")
         return jsonify({'error': 'No valid settings provided for update.'}), 400

    # Merge with existing settings before saving to preserve others
    updated_full_settings = app_current_settings.copy() # Get a copy of current settings from config.py
    updated_full_settings.update(new_settings)

    if save_settings(updated_full_settings):
        # Update Flask app config dynamically for some settings if possible
        if 'HTTP_PORT' in new_settings:
            current_app.config['HTTP_PORT'] = new_settings['HTTP_PORT']
        if 'AUTO_START_HTTP' in new_settings:
            current_app.config['AUTO_START_HTTP'] = new_settings['AUTO_START_HTTP']

        return jsonify({'message': 'Settings updated. Port changes may require an application restart to take effect.', 'updated_settings': new_settings}), 200
    else:
        return jsonify({'error': 'Failed to save settings to file.'}), 500
