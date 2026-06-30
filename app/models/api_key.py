import uuid
import secrets
import hashlib
from app import db
from datetime import datetime, timezone

class ApiKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(128), nullable=False)
    public_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    secret_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    creator = db.relationship('User', backref='api_keys')
    
    @staticmethod
    def generate_keys():
        # Generate a public/private key pair
        public_key = f"slopit_pk_{secrets.token_hex(12)}"  # slopit_pk_<24 hex chars>
        secret_key = f"slopit_sk_{secrets.token_hex(24)}"  # slopit_sk_<48 hex chars>
        return public_key, secret_key
    
    @staticmethod
    def hash_secret(secret_key):
        return hashlib.sha256(secret_key.encode()).hexdigest()
    
    def verify_secret(self, secret_key):
        return self.secret_hash == self.hash_secret(secret_key)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'public_key': self.public_key,
            'is_active': self.is_active,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat()
        }