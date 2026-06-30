import uuid
from app import db
from datetime import datetime

class Collection(db.Model):
    __tablename__ = 'collections'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(64), unique=True, nullable=False)
    label = db.Column(db.String(128), nullable=False)
    is_singleton = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    fields = db.relationship('Field', backref='collection', lazy='dynamic', 
                             cascade='all, delete-orphan')
    entries = db.relationship('Entry', backref='collection', lazy='dynamic',
                             cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'is_singleton': self.is_singleton,
            'fields': [f.to_dict() for f in self.fields.all()],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }