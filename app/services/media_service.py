import threading
import uuid
import os
from werkzeug.utils import secure_filename
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


def _upload_to_s3_async(app, media_id, file_path, folder, mime_type, original_filename):
    with app.app_context():
        media = Media.query.get(media_id)
        if not media:
            return

        try:
            with open(file_path, 'rb') as f:
                result = S3Service.upload_file(
                    f,
                    folder=folder,
                    allowed_extensions=None
                )

            media.s3_key = result['key']
            media.url = result['url']
            media.size = result['size']
            media.mime_type = result['content_type']
            media.filename = original_filename
            db.session.commit()

        except Exception as e:
            app.logger.error(f'Async S3 upload failed: {str(e)}')
        finally:
            try:
                os.remove(file_path)
            except:
                pass


def upload_media(file, user_id, folder='general', alt_text=None, caption=None):
    mime = file.content_type or 'application/octet-stream'
    media_type = get_media_type(mime)

    if media_type == MediaType.IMAGE:
        allowed = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'}
    elif media_type == MediaType.VIDEO:
        allowed = {'mp4', 'webm', 'mov', 'avi'}
    else:
        allowed = {'pdf', 'doc', 'docx', 'txt', 'csv'}

    original_filename = secure_filename(file.filename or 'file')
    ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else ''
    if ext not in allowed:
        raise ValueError(f'File type .{ext} not allowed. Accepted: {", ".join(allowed)}')

    max_size = current_app.config.get('MAX_UPLOAD_SIZE', 10 * 1024 * 1024)
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > max_size:
        raise ValueError(f'File too large. Max {max_size // (1024 * 1024)}MB')

    width, height = None, None
    file_data = file.read()
    if media_type == MediaType.IMAGE:
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(file_data))
            width, height = img.size
        except:
            pass

    temp_dir = os.path.join(current_app.instance_path, 'tmp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f'{uuid.uuid4().hex}.{ext}')

    with open(temp_path, 'wb') as f:
        f.write(file_data)

    media = Media(
        filename=original_filename,
        s3_key='',
        url='',
        media_type=media_type,
        mime_type=mime,
        size=size,
        width=width,
        height=height,
        alt_text=alt_text,
        caption=caption,
        folder=folder,
        uploaded_by=user_id
    )

    db.session.add(media)
    db.session.commit()

    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_upload_to_s3_async,
        args=(app, media.id, temp_path, folder, mime, original_filename),
        daemon=True
    )
    thread.start()

    return media


def delete_media(media_id):
    media = Media.query.get(media_id)
    if media:
        if media.s3_key:
            try:
                S3Service.delete_file(media.s3_key)
            except:
                pass
        db.session.delete(media)
        db.session.commit()
        return True
    return False