import uuid
from app import db

class EntryValue(db.Model):
    __tablename__ = 'entry_values'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entry_id = db.Column(db.String(36), db.ForeignKey('entries.id'), nullable=False)
    field_id = db.Column(db.String(36), db.ForeignKey('fields.id'), nullable=False)
    value = db.Column(db.Text, nullable=True)
    
    field = db.relationship('Field', lazy='joined')
    
    __table_args__ = (
        db.UniqueConstraint('entry_id', 'field_id', name='unique_entry_field'),
    )