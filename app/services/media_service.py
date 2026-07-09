from app.services.s3 import S3Service
from app.models.media import Media, MediaType
from app import db
from flask import current_app

def get_media_type(mime_type):
    if mime_type.startswith('image/'):
        return MediaType.IMAGE
    elif mime_type.startswith('video/'):
        return MediaType.VIDEO
    return MediaType.DOCUMENT

def upload_media(file, user_id, folder='general', alt_text=None, caption=None):
    mime = file.content_type or 'application/octet-stream'
    media_type = get_media_type(mime)
    
    if media_type == MediaType.IMAGE:
        allowed = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'}
    elif media_type == MediaType.VIDEO:
        allowed = {'mp4', 'webm', 'mov', 'avi'}
    else:
        allowed = {'pdf', 'doc', 'docx', 'txt', 'csv'}
    
    result = S3Service.upload_file(
        file,
        folder=folder,
        allowed_extensions=allowed
    )
    
    width, height = None, None
    if media_type == MediaType.IMAGE:
        try:
            from PIL import Image
            import io
            file.seek(0)
            img = Image.open(io.BytesIO(file.read()))
            width, height = img.size
            file.seek(0)
        except:
            pass
    
    media = Media(
        filename=result['filename'],
        s3_key=result['key'],
        url=result['url'],
        media_type=media_type,
        mime_type=result['content_type'],
        size=result['size'],
        width=width,
        height=height,
        alt_text=alt_text,
        caption=caption,
        folder=folder,
        uploaded_by=user_id
    )
    
    db.session.add(media)
    db.session.commit()
    
    return media

def delete_media(media_id):
    media = Media.query.get(media_id)
    if media:
        try:
            S3Service.delete_file(media.s3_key)
        except:
            pass
        db.session.delete(media)
        db.session.commit()
        return True
    return False