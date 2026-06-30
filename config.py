import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SITE_NAME = os.environ.get('SITE_NAME', 'SlopIt')
    SITE_URL = os.environ.get('SITE_URL', 'http://localhost:5000')
    SITE_DESCRIPTION = os.environ.get('SITE_DESCRIPTION', 'A lightweight, self-hosted CMS')
    SITE_EMAIL = os.environ.get('SITE_EMAIL', 'noreply@slopit.local')
    
    TIMEZONE = os.environ.get('TIMEZONE', 'UTC')
    
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', SITE_EMAIL)

    S3_ENDPOINT_URL = os.environ.get('S3_ENDPOINT_URL')
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'slopit-media')
    S3_REGION = os.environ.get('S3_REGION', 'auto')
    S3_ACCESS_KEY_ID = os.environ.get('S3_ACCESS_KEY_ID')
    S3_SECRET_ACCESS_KEY = os.environ.get('S3_SECRET_ACCESS_KEY')
    S3_PUBLIC_URL = os.environ.get('S3_PUBLIC_URL', '')
    MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE', 10 * 1024 * 1024))  # 10MB