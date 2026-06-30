from app.main import bp
from app import db
from flask import render_template, jsonify

@bp.route('/')
def index():
    return render_template('main/home.html')

@bp.route('/health')
def health_check():
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'database': db_status
    })