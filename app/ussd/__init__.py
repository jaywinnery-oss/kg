"""USSD Blueprint for Africa's Talking integration"""
from flask import Blueprint

bp = Blueprint('ussd', __name__)

from app.ussd import routes