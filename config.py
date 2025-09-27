"""
Configuration settings for the Emergency Response USSD System
Includes security configurations and environment-specific settings
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class with security defaults"""
    
    # Basic Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///emergency_response.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_DEFAULT = "100 per hour"
    USSD_RATE_LIMIT = "3 per hour"  # Max 3 USSD requests per phone number per hour
    SMS_RATE_LIMIT = "5 per hour"   # Max 5 SMS per phone number per hour
    
    # Africa's Talking Configuration
    AFRICAS_TALKING_USERNAME = os.environ.get('AT_USERNAME', 'sandbox')
    AFRICAS_TALKING_API_KEY = os.environ.get('AT_API_KEY', '')
    USSD_SERVICE_CODE = os.environ.get('USSD_SERVICE_CODE', '*384#')
    USSD_CHANNEL = os.environ.get('USSD_CHANNEL', '17925')
    
    # SMS Configuration
    SMS_SENDER_ID = os.environ.get('SMS_SENDER_ID', 'EMERGENCY')
    
    # Encryption Configuration
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or 'default-key-change-in-production'
    
    # Audit and Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', '90'))
    
    # Payment Configuration
    PAYMENT_GATEWAY_URL = os.environ.get('PAYMENT_GATEWAY_URL', '')
    PAYMENT_API_KEY = os.environ.get('PAYMENT_API_KEY', '')
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    }
    
    # NDPR Compliance
    DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS', '365'))
    PRIVACY_POLICY_URL = os.environ.get('PRIVACY_POLICY_URL', '/privacy')
    
    # Geographic Configuration
    DEFAULT_COUNTRY = 'NG'
    DEFAULT_STATE = 'Kogi'
    MAX_LOCATION_RADIUS_KM = 50  # Maximum radius for resource matching

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    WTF_CSRF_ENABLED = False  # Disable CSRF for easier testing

class ProductionConfig(Config):
    """Production configuration with enhanced security"""
    DEBUG = False
    TESTING = False
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    
    # Stricter rate limits for production
    RATELIMIT_DEFAULT = "50 per hour"
    USSD_RATE_LIMIT = "2 per hour"
    SMS_RATE_LIMIT = "3 per hour"

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}