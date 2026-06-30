import uuid
from app import db

class RepeaterBlock(db.Model):
    __tablename__ = 'repeater_blocks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    field_id = db.Column(db.String(36), db.ForeignKey('fields.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    label = db.Column(db.String(128), nullable=False)
    order = db.Column(db.Integer, default=0)
    
    field = db.relationship('Field', backref=db.backref('repeater_blocks', lazy='dynamic', cascade='all, delete-orphan'))
    
    sub_fields = db.relationship('RepeaterSubField', backref='block', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'order': self.order,
            'sub_fields': [sf.to_dict() for sf in self.sub_fields.order_by(RepeaterSubField.order).all()]
        }