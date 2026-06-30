import uuid
from app import db
from app.models.field import FieldType

class RepeaterSubField(db.Model):
    __tablename__ = 'repeater_sub_fields'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    block_id = db.Column(db.String(36), db.ForeignKey('repeater_blocks.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    label = db.Column(db.String(128), nullable=False)
    field_type = db.Column(db.Enum(FieldType), nullable=False)
    required = db.Column(db.Boolean, default=False)
    options = db.Column(db.JSON, nullable=True)
    default_value = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'field_type': self.field_type.value,
            'required': self.required,
            'options': self.options,
            'default_value': self.default_value,
            'order': self.order
        }