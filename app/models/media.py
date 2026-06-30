import uuid
from app import db
from datetime import datetime, timezone

class MediaType:
    IMAGE = 'image'
    VIDEO = 'video'
    DOCUMENT = 'document'

class Media(db.Model):
    __tablename__ = 'media'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(256), nullable=False)
    s3_key = db.Column(db.String(512), nullable=False)
    url = db.Column(db.String(1024), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)  # image, video, document
    mime_type = db.Column(db.String(128), nullable=False)
    size = db.Column(db.BigInteger, nullable=False)        # size in bytes
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    alt_text = db.Column(db.String(512), nullable=True)
    caption = db.Column(db.Text, nullable=True)
    folder = db.Column(db.String(128), default='general')
    uploaded_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    uploader = db.relationship('User', backref='media_uploads')
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'url': self.url,
            'media_type': self.media_type,
            'mime_type': self.mime_type,
            'size': self.size,
            'width': self.width,
            'height': self.height,
            'alt_text': self.alt_text,
            'caption': self.caption,
            'folder': self.folder,
            'created_at': self.created_at.isoformat()
        }
    
    def is_image(self):
        return self.media_type == MediaType.IMAGE
    
    def is_video(self):
        return self.media_type == MediaType.VIDEO