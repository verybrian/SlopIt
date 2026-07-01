import os
import pytz
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    tz_name = os.environ.get('TIMEZONE', 'UTC')
    app.config['TIMEZONE'] = pytz.timezone(tz_name)

    from app.filters import timeago
    app.jinja_env.filters['timeago'] = timeago
    
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.api import bp as api_bp
    app.register_blueprint(api_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp)
    
    with app.app_context():
        db.create_all()
    
    @app.context_processor
    def inject_site_config():
        from app.models import Collection
        return {
            'site_name': app.config['SITE_NAME'],
            'site_description': app.config['SITE_DESCRIPTION'],
            'site_url': app.config['SITE_URL'],
            'config': app.config,
            'get_collections': lambda: Collection.query.order_by(Collection.label).all(),
        }
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(str(user_id))