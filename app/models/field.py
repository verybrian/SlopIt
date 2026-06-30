import uuid
from app import db
import enum

class FieldType(enum.Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    RICH_TEXT = "rich_text"
    IMAGE = "image"
    DATE = "date"
    BOOLEAN = "boolean"
    SELECT = "select"
    NUMBER = "number"

class Field(db.Model):
    __tablename__ = 'fields'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = db.Column(db.String(36), db.ForeignKey('collections.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    label = db.Column(db.String(128), nullable=False)
    field_type = db.Column(db.Enum(FieldType), nullable=False)
    required = db.Column(db.Boolean, default=False)
    options = db.Column(db.JSON, nullable=True)
    order = db.Column(db.Integer, default=0)
    default_value = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'field_type': self.field_type.value,
            'required': self.required,
            'options': self.options,
            'order': self.order,
            'default_value': self.default_value
        }