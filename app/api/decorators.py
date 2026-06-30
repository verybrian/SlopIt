from functools import wraps
from flask import request, jsonify, current_app
from app.models.api_key import ApiKey

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        public_key = request.headers.get('X-API-Key')
        
        if not public_key:
            return jsonify({'error': 'API key required. Send it as X-API-Key header.'}), 401
        
        api_key = ApiKey.query.filter_by(public_key=public_key, is_active=True).first()
        
        if not api_key:
            return jsonify({'error': 'Invalid or inactive API key.'}), 403
        
        from app import db
        from datetime import datetime, timezone
        api_key.last_used_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return f(*args, **kwargs)
    
    return decorated_function