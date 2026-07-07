from flask import Blueprint

bp = Blueprint('admin', __name__, url_prefix='/d')

from app.admin import routes