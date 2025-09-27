"""
Emergency Response USSD System
Secure Flask application factory with comprehensive security features
"""
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from logging.handlers import RotatingFileHandler
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

def create_app(config_name='default'):
    """Application factory with security configurations"""
    app = Flask(__name__)
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    
    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
        for header, value in app.config['SECURITY_HEADERS'].items():
            response.headers[header] = value
        return response
    
    # Request logging middleware
    @app.before_request
    def log_request_info():
        """Log all incoming requests for security monitoring"""
        if not app.config.get('TESTING'):
            app.logger.info(f"Request: {request.method} {request.url} from {request.remote_addr}")
    
    # Error handlers
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handle rate limit exceeded errors"""
        app.logger.warning(f"Rate limit exceeded for {request.remote_addr}: {e}")
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'retry_after': getattr(e, 'retry_after', 3600)
        }), 429
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors"""
        return jsonify({
            'error': 'Bad Request',
            'message': 'Invalid request format'
        }), 400
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors"""
        db.session.rollback()
        app.logger.error(f"Internal error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
    
    # Register blueprints
    from app.ussd import bp as ussd_bp
    app.register_blueprint(ussd_bp, url_prefix='/ussd')
    
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.provider import bp as provider_bp
    app.register_blueprint(provider_bp, url_prefix='/provider')
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/emergency_response.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Emergency Response System startup')
    
    return app

# Import models to ensure they are registered with SQLAlchemy
from app import models