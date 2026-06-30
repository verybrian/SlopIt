import uuid
from app import db

class RepeaterItem(db.Model):
    __tablename__ = 'repeater_items'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entry_value_id = db.Column(db.String(36), db.ForeignKey('entry_values.id'), nullable=False)
    block_id = db.Column(db.String(36), db.ForeignKey('repeater_blocks.id'), nullable=False)
    order = db.Column(db.Integer, default=0)
    
    entry_value = db.relationship('EntryValue', backref=db.backref('repeater_items', lazy='dynamic', cascade='all, delete-orphan'))
    block = db.relationship('RepeaterBlock', lazy='joined')
    
    values = db.relationship('RepeaterItemValue', backref='item', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        data = {
            '_type': self.block.name,
            '_order': self.order
        }
        for value in self.values.all():
            data[value.sub_field.name] = value.value
        return data