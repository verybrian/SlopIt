import uuid
from app import db
from datetime import datetime
from app.models.entry_value import EntryValue
from app.models.field import Field


class Entry(db.Model):
    __tablename__ = 'entries'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = db.Column(db.String(36), db.ForeignKey('collections.id'), nullable=False)
    slug = db.Column(db.String(256), nullable=True)
    status = db.Column(db.String(20), default='draft')
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    values = db.relationship('EntryValue', backref='entry', lazy='dynamic',
                            cascade='all, delete-orphan')
    
    def get_value(self, field_name):
        value = EntryValue.query.join(Field).filter(
            EntryValue.entry_id == self.id,
            Field.name == field_name
        ).first()
        return value.value if value else None
    
    def to_dict(self, flat=True):
        if flat:
            data = {
                'id': self.id,
                'slug': self.slug,
                'status': self.status,
                'created_at': self.created_at.isoformat(),
                'updated_at': self.updated_at.isoformat()
            }
            for value in self.values.all():
                field = value.field
                
                if field.field_type.value == 'repeater':
                    # Get repeater items in order
                    items = RepeaterItem.query.filter_by(
                        entry_value_id=value.id
                    ).order_by(RepeaterItem.order).all()
                    data[field.name] = [item.to_dict() for item in items]
                else:
                    data[field.name] = value.value
            
            return data
        else:
            return {
                'id': self.id,
                'slug': self.slug,
                'status': self.status,
                'values': {v.field.name: v.value for v in self.values.all()},
                'created_at': self.created_at.isoformat(),
                'updated_at': self.updated_at.isoformat()
            }