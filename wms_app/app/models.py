from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Tray(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True, nullable=False)
    location_count = db.Column(db.Integer, nullable=False)
    locations = db.relationship('Location', backref='tray', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Tray {self.name}>'

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tray_id = db.Column(db.Integer, db.ForeignKey('tray.id'), nullable=False)
    position_identifier = db.Column(db.String(64), nullable=False) # e.g., "A1", "1", "Slot 1"
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    sample_record_id = db.Column(db.Integer, db.ForeignKey('sample_record.id'), nullable=True)
    sample_record = db.relationship('SampleRecord', backref=db.backref('location', uselist=False))

    # Ensure a position is unique within a tray
    __table_args__ = (db.UniqueConstraint('tray_id', 'position_identifier', name='_tray_position_uc'),)

    def __repr__(self):
        return f'<Location {self.tray.name} - {self.position_identifier}>'

class SampleRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sample_id_str = db.Column(db.String(128), unique=True, index=True, nullable=False) # The user-facing sample ID
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # The relationship to Location is defined in Location model via backref

    def __repr__(self):
        return f'<SampleRecord {self.sample_id_str}>'
