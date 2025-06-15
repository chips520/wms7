import json
from tests.base_test import BaseTestCase
from wms_app.app.models import db, Tray, Location, SampleRecord

class TestApiEndpoints(BaseTestCase):

    def test_01_create_tray(self):
        response = self.create_tray(name="AGV_Tray1", location_count=10)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['name'], "AGV_Tray1")
        self.assertEqual(data['location_count'], 10)
        self.assertIn('Tray "AGV_Tray1" created with 10 locations.', data['message'])

        # Verify locations were created
        tray = Tray.query.filter_by(name="AGV_Tray1").first()
        self.assertIsNotNone(tray)
        self.assertEqual(Location.query.filter_by(tray_id=tray.id).count(), 10)

    def test_02_get_trays(self):
        self.create_tray(name="TrayA", location_count=3)
        self.create_tray(name="TrayB", location_count=2)
        response = self.client.get('/api/trays')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], "TrayA")

    def test_03_get_specific_tray(self):
        self.create_tray(name="DetailTray", location_count=1)
        tray = Tray.query.first() # Assumes only one tray from this test function
        response = self.client.get(f'/api/trays/{tray.id}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], "DetailTray")
        self.assertEqual(len(data['locations']), 1)

    def test_04_delete_tray(self):
        self.create_tray(name="ToDelete", location_count=1)
        tray_to_delete = Tray.query.filter_by(name="ToDelete").first()
        self.assertIsNotNone(tray_to_delete)

        response = self.client.delete(f'/api/trays/{tray_to_delete.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Tray.query.filter_by(name="ToDelete").first())
        self.assertEqual(Location.query.filter_by(tray_id=tray_to_delete.id).count(), 0)

    def test_05_get_tray_locations(self):
        self.create_tray(name="LocTray", location_count=3)
        tray = Tray.query.first()
        response = self.client.get(f'/api/trays/{tray.id}/locations')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['position_identifier'], 'Pos1')

    def test_06_enable_disable_location(self):
        self.create_tray(name="EnableDisableTray", location_count=1)
        location = Location.query.first()

        # Disable
        response = self.client.put(f'/api/locations/{location.id}/disable')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Location.query.get(location.id).is_enabled)

        # Enable
        response = self.client.put(f'/api/locations/{location.id}/enable')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Location.query.get(location.id).is_enabled)

    def test_07_get_empty_location(self):
        self.create_tray(name="EmptyLocTray", location_count=2)
        tray = Tray.query.first()

        response = self.client.get(f'/api/trays/{tray.id}/empty_location')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsNotNone(data['id']) # Should get the first location

        # Occupy first location
        first_loc_id = data['id']
        self.place_sample(sample_id_str="S_Fill1", tray_id=tray.id, location_id=first_loc_id)

        response = self.client.get(f'/api/trays/{tray.id}/empty_location')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertNotEqual(data['id'], first_loc_id) # Should get the second one

    def test_08_place_sample_auto_assign(self):
        self.create_tray(name="PlaceSampleTray", location_count=1)
        tray = Tray.query.first()
        response = self.place_sample(sample_id_str="S_Auto", tray_id=tray.id)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['sample_id_str'], "S_Auto")
        self.assertIsNotNone(SampleRecord.query.filter_by(sample_id_str="S_Auto").first())
        self.assertIsNotNone(Location.query.filter_by(sample_record_id=SampleRecord.query.filter_by(sample_id_str="S_Auto").first().id).first())

    def test_09_place_sample_specific_location(self):
        self.create_tray(name="PlaceSampleSpec", location_count=1)
        tray = Tray.query.first()
        location = Location.query.filter_by(tray_id=tray.id).first()
        response = self.place_sample(sample_id_str="S_Spec", tray_id=tray.id, location_id=location.id)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.query.get(location.id).sample_record.sample_id_str, "S_Spec")

    def test_10_place_sample_error_duplicate_sample(self):
        self.create_tray(name="DupSampleTray", location_count=2)
        tray = Tray.query.first()
        self.place_sample(sample_id_str="S_Dup", tray_id=tray.id) # First placement
        response = self.place_sample(sample_id_str="S_Dup", tray_id=tray.id) # Second attempt
        self.assertEqual(response.status_code, 409) # Conflict
        data = response.get_json()
        self.assertIn('already exists', data['error'])

    def test_11_place_sample_error_no_empty_location(self):
        self.create_tray(name="NoEmptyTray", location_count=1)
        tray = Tray.query.first()
        self.place_sample(sample_id_str="S_FillAll", tray_id=tray.id) # Fill the only location
        response = self.place_sample(sample_id_str="S_NoRoom", tray_id=tray.id) # Try to place another
        self.assertEqual(response.status_code, 404) # As per current logic, finds no empty location
        data = response.get_json()
        self.assertIn('No empty and enabled location found', data['error'])

    def test_12_place_sample_error_location_occupied(self):
        self.create_tray(name="OccLocTray", location_count=1)
        tray = Tray.query.first()
        loc = Location.query.filter_by(tray_id=tray.id).first()
        self.place_sample(sample_id_str="S_Occupier", tray_id=tray.id, location_id=loc.id) # Occupy

        response = self.place_sample(sample_id_str="S_Intruder", tray_id=tray.id, location_id=loc.id) # Try to place in same
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('is already occupied', data['error'])

    def test_13_place_sample_error_location_disabled(self):
        self.create_tray(name="DisabledLocTray", location_count=1)
        tray = Tray.query.first()
        loc = Location.query.filter_by(tray_id=tray.id).first()
        self.client.put(f'/api/locations/{loc.id}/disable') # Disable it

        response = self.place_sample(sample_id_str="S_TryDisabled", tray_id=tray.id, location_id=loc.id)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('is disabled', data['error'])

    def test_14_get_sample_location(self):
        self.create_tray(name="QuerySampleTray", location_count=1)
        tray = Tray.query.first()
        self.place_sample(sample_id_str="S_QueryMe", tray_id=tray.id)

        response = self.client.get('/api/samples/S_QueryMe')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['sample_id_str'], "S_QueryMe")
        self.assertEqual(data['tray_id'], tray.id)

    def test_15_clear_location(self):
        self.create_tray(name="ClearLocTray", location_count=1)
        tray = Tray.query.first()
        loc = Location.query.filter_by(tray_id=tray.id).first()
        self.place_sample(sample_id_str="S_Clearable", tray_id=tray.id, location_id=loc.id)

        sample_record = SampleRecord.query.filter_by(sample_id_str="S_Clearable").first()
        self.assertIsNotNone(sample_record)

        response = self.client.delete(f'/api/locations/{loc.id}/clear')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Location.query.get(loc.id).sample_record_id)
        self.assertIsNone(SampleRecord.query.filter_by(sample_id_str="S_Clearable").first()) # Check sample record is deleted

    def test_16_clear_all_locations_on_tray(self):
        self.create_tray(name="ClearAllTray", location_count=2)
        tray = Tray.query.first()
        locs = Location.query.filter_by(tray_id=tray.id).all()
        self.place_sample(sample_id_str="S_BulkClear1", tray_id=tray.id, location_id=locs[0].id)
        self.place_sample(sample_id_str="S_BulkClear2", tray_id=tray.id, location_id=locs[1].id)

        self.assertEqual(SampleRecord.query.count(), 2)

        response = self.client.post(f'/api/trays/{tray.id}/clear_all')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Location.query.filter(Location.sample_record_id != None).count(), 0)
        self.assertEqual(SampleRecord.query.count(), 0) # Check all sample records deleted

    def test_17_disable_occupied_location_error(self):
        self.create_tray(name="DisableOccupiedTray", location_count=1)
        tray = Tray.query.first()
        loc = Location.query.filter_by(tray_id=tray.id).first()
        self.place_sample(sample_id_str="S_OccupyingDisable", tray_id=tray.id, location_id=loc.id)

        response = self.client.put(f'/api/locations/{loc.id}/disable')
        self.assertEqual(response.status_code, 400) # Should fail
        data = response.get_json()
        self.assertIn('Cannot disable occupied location', data['error'])
        self.assertTrue(Location.query.get(loc.id).is_enabled) # Should still be enabled

if __name__ == '__main__':
    unittest.main()
