import boto3
import uuid
import mimetypes
from flask import current_app
from werkzeug.utils import secure_filename

class S3Service:
    _client = None
    
    @classmethod
    def get_client(cls):
        """Get or create S3 client"""
        if cls._client is None:
            cls._client = boto3.client(
                's3',
                endpoint_url=current_app.config['S3_ENDPOINT_URL'],
                region_name=current_app.config['S3_REGION'],
                aws_access_key_id=current_app.config['S3_ACCESS_KEY_ID'],
                aws_secret_access_key=current_app.config['S3_SECRET_ACCESS_KEY']
            )
        return cls._client
    
    @classmethod
    def upload_file(cls, file, folder='uploads', allowed_extensions=None):
        if not file or not file.filename:
            raise ValueError('No file provided')
        
        # Validate extension
        if allowed_extensions:
            ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
            if ext not in allowed_extensions:
                raise ValueError(f'File type .{ext} not allowed. Accepted: {", ".join(allowed_extensions)}')
        
        max_size = current_app.config.get('MAX_UPLOAD_SIZE', 10 * 1024 * 1024)
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > max_size:
            raise ValueError(f'File too large. Max {max_size // (1024 * 1024)}MB')
        
        original_filename = secure_filename(file.filename)
        ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else ''
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        key = f"{folder}/{unique_name}"
        
        content_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
        
        client = cls.get_client()
        bucket = current_app.config['S3_BUCKET_NAME']
        
        client.upload_fileobj(
            file,
            bucket,
            key,
            ExtraArgs={
                'ContentType': content_type,
                'ACL': 'public-read'
            }
        )
        
        public_url = current_app.config.get('S3_PUBLIC_URL', '')
        if public_url:
            url = f"{public_url.rstrip('/')}/{key}"
        else:
            url = f"https://{bucket}.s3.amazonaws.com/{key}"
        
        return {
            'url': url,
            'key': key,
            'filename': original_filename,
            'content_type': content_type,
            'size': size
        }
    
    @classmethod
    def delete_file(cls, key):
        client = cls.get_client()
        bucket = current_app.config['S3_BUCKET_NAME']
        client.delete_object(Bucket=bucket, Key=key)