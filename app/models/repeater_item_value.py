import uuid
from app import db

class RepeaterItemValue(db.Model):
    __tablename__ = 'repeater_item_values'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = db.Column(db.String(36), db.ForeignKey('repeater_items.id'), nullable=False)
    sub_field_id = db.Column(db.String(36), db.ForeignKey('repeater_sub_fields.id'), nullable=False)
    value = db.Column(db.Text, nullable=True)
    
    sub_field = db.relationship('RepeaterSubField', lazy='joined')
    
    __table_args__ = (
        db.UniqueConstraint('item_id', 'sub_field_id', name='unique_item_subfield'),
    )