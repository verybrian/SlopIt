import uuid
from app import db
from datetime import datetime, timezone


class Entry(db.Model):
    __tablename__ = 'entries'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = db.Column(db.String(36), db.ForeignKey('collections.id'), nullable=False)
    slug = db.Column(db.String(256), nullable=True)
    data = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def get_value(self, field_name):
        return (self.data or {}).get(field_name)

    def to_dict(self):
        out = {
            'id': self.id,
            'slug': self.slug,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        out.update(self.data or {})
        return out