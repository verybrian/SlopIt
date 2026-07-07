from functools import wraps
from flask import request, jsonify
from app.models.api_key import ApiKey

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({'error': 'API key required. Send it as X-API-Key header.'}), 401
        
        key = ApiKey.query.filter_by(key=api_key, is_active=True).first()
        
        if not key:
            return jsonify({'error': 'Invalid or inactive API key.'}), 403
        
        from app import db
        from datetime import datetime, timezone
        key.last_used_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return f(*args, **kwargs)
    
    return decorated_function