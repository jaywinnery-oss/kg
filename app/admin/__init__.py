"""Admin Blueprint for administrative interface"""
from flask import Blueprint

bp = Blueprint('admin', __name__)

from app.admin import routes