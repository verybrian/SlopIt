import uuid
import enum
from app import db
from datetime import datetime, timezone


class CollectionKind(enum.Enum):
    POST = "post"
    SECTION = "section"
    LIST = "list"


class Collection(db.Model):
    __tablename__ = 'collections'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(64), unique=True, nullable=False)
    label = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    kind = db.Column(db.Enum(CollectionKind), nullable=False, default=CollectionKind.POST)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    fields = db.relationship('Field', backref='collection', lazy='dynamic', cascade='all, delete-orphan')
    entries = db.relationship('Entry', backref='collection', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'description': self.description,
            'kind': self.kind.value,
            'fields': [f.to_dict() for f in self.fields.all()],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }