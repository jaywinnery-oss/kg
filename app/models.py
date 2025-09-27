"""
Database models for Emergency Response USSD System
Includes security features: encryption, hashing, audit logging
"""
from app import db
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import secrets
import json
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash
import base64

class ResourceType(Enum):
    """Types of emergency resources"""
    SHELTER = "shelter"
    FOOD = "food"
    TRANSPORT = "transport"

class RequestStatus(Enum):
    """Status of emergency requests"""
    PENDING = "pending"
    MATCHED = "matched"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class UserRole(Enum):
    """User roles for access control"""
    CALLER = "caller"           # Flood victim
    VOLUNTEER = "volunteer"     # Individual volunteer
    NGO = "ngo"                # NGO representative
    GOVERNMENT = "government"   # Government officer
    ADMIN = "admin"            # System administrator

class PaymentStatus(Enum):
    """Payment transaction status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

def encrypt_data(data):
    """Encrypt sensitive data using Fernet encryption"""
    if not data:
        return None
    key = base64.urlsafe_b64encode(b'emergency_response_key_32_bytes!')  # In production, use proper key management
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data):
    """Decrypt sensitive data"""
    if not encrypted_data:
        return None
    key = base64.urlsafe_b64encode(b'emergency_response_key_32_bytes!')
    f = Fernet(key)
    return f.decrypt(encrypted_data.encode()).decode()

def hash_phone_number(phone_number):
    """Hash phone number for privacy while maintaining searchability"""
    salt = "emergency_response_salt"  # In production, use proper salt management
    return hashlib.sha256((phone_number + salt).encode()).hexdigest()

class AuditLog(db.Model):
    """Audit log for all system actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 support
    user_agent = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON string for additional details
    session_id = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} at {self.timestamp}>'

class User(db.Model):
    """User model with encrypted PII and role-based access"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    phone_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    encrypted_phone = db.Column(db.Text, nullable=True)  # Encrypted actual phone number
    encrypted_name = db.Column(db.Text, nullable=True)   # Encrypted name
    role = db.Column(db.Enum(UserRole), default=UserRole.CALLER, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Security fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    emergency_requests = db.relationship('EmergencyRequest', backref='user', lazy='dynamic')
    ussd_sessions = db.relationship('USSDSession', backref='user', lazy='dynamic')
    
    def __init__(self, phone_number, name=None, role=UserRole.CALLER):
        self.phone_hash = hash_phone_number(phone_number)
        self.encrypted_phone = encrypt_data(phone_number)
        if name:
            self.encrypted_name = encrypt_data(name)
        self.role = role
    
    @property
    def phone_number(self):
        """Decrypt and return phone number"""
        return decrypt_data(self.encrypted_phone)
    
    @property
    def name(self):
        """Decrypt and return name"""
        return decrypt_data(self.encrypted_name) if self.encrypted_name else None
    
    def is_rate_limited(self, action_type='ussd', limit_per_hour=3):
        """Check if user is rate limited for specific action"""
        from app.models import AuditLog
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_actions = AuditLog.query.filter(
            AuditLog.user_id == self.id,
            AuditLog.action == action_type,
            AuditLog.timestamp > one_hour_ago
        ).count()
        return recent_actions >= limit_per_hour
    
    def __repr__(self):
        return f'<User {self.phone_hash[:8]}... ({self.role.value})>'

class Provider(db.Model):
    """Service providers (NGOs, Government, Volunteers)"""
    __tablename__ = 'providers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organization_name = db.Column(db.String(200), nullable=False)
    encrypted_contact_person = db.Column(db.Text, nullable=True)
    encrypted_email = db.Column(db.Text, nullable=True)
    verification_status = db.Column(db.String(20), default='pending')  # pending, verified, rejected
    verification_documents = db.Column(db.Text, nullable=True)  # JSON array of document URLs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Payment information
    encrypted_bank_account = db.Column(db.Text, nullable=True)
    encrypted_bank_name = db.Column(db.Text, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='provider_profile')
    resources = db.relationship('Resource', backref='provider', lazy='dynamic')
    
    def __repr__(self):
        return f'<Provider {self.organization_name}>'

class Resource(db.Model):
    """Emergency resources with location and capacity tracking"""
    __tablename__ = 'resources'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    resource_type = db.Column(db.Enum(ResourceType), nullable=False)
    
    # Location information
    location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Capacity management
    total_capacity = db.Column(db.Integer, nullable=False, default=0)
    available_capacity = db.Column(db.Integer, nullable=False, default=0)
    
    # Contact information (encrypted)
    encrypted_contact_phone = db.Column(db.Text, nullable=True)
    
    # Pricing (for paid services)
    price_per_unit = db.Column(db.Float, default=0.0)  # 0 for free services
    currency = db.Column(db.String(3), default='NGN')
    
    # Status and metadata
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    emergency_requests = db.relationship('EmergencyRequest', backref='resource', lazy='dynamic')
    
    @property
    def contact_phone(self):
        """Decrypt and return contact phone"""
        return decrypt_data(self.encrypted_contact_phone) if self.encrypted_contact_phone else None
    
    def update_capacity(self, used_capacity):
        """Update available capacity safely"""
        if self.available_capacity >= used_capacity:
            self.available_capacity -= used_capacity
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def __repr__(self):
        return f'<Resource {self.name} ({self.resource_type.value})>'

class EmergencyRequest(db.Model):
    """Emergency requests with audit trail and reference numbers"""
    __tablename__ = 'emergency_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=True)
    
    # Request details
    resource_type = db.Column(db.Enum(ResourceType), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    quantity_needed = db.Column(db.Integer, default=1)
    
    # Status tracking
    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    matched_at = db.Column(db.DateTime, nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Additional information
    notes = db.Column(db.Text, nullable=True)
    priority_level = db.Column(db.Integer, default=1)  # 1=low, 5=critical
    
    # Payment information
    total_cost = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Relationships
    payments = db.relationship('Payment', backref='emergency_request', lazy='dynamic')
    
    def __init__(self, user_id, resource_type, location, **kwargs):
        self.user_id = user_id
        self.resource_type = resource_type
        self.location = location
        self.reference_number = self.generate_reference_number()
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @staticmethod
    def generate_reference_number():
        """Generate unique reference number for tracking"""
        prefix = "ER"  # Emergency Response
        timestamp = datetime.utcnow().strftime("%y%m%d")
        random_part = secrets.token_hex(3).upper()
        return f"{prefix}{timestamp}{random_part}"
    
    def __repr__(self):
        return f'<EmergencyRequest {self.reference_number} ({self.status.value})>'

class USSDSession(db.Model):
    """USSD session management with security tracking"""
    __tablename__ = 'ussd_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Session state
    current_step = db.Column(db.String(50), default='start')
    session_data = db.Column(db.Text, nullable=True)  # JSON string for session variables
    
    # Security tracking
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, session_id, user_id, **kwargs):
        self.session_id = session_id
        self.user_id = user_id
        self.expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10-minute session timeout
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def is_expired(self):
        """Check if session has expired"""
        return datetime.utcnow() > self.expires_at
    
    def extend_session(self, minutes=10):
        """Extend session expiry time"""
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        self.last_activity = datetime.utcnow()
    
    def get_session_data(self):
        """Get session data as dictionary"""
        return json.loads(self.session_data) if self.session_data else {}
    
    def set_session_data(self, data):
        """Set session data from dictionary"""
        self.session_data = json.dumps(data)
    
    def __repr__(self):
        return f'<USSDSession {self.session_id} ({self.current_step})>'

class Payment(db.Model):
    """Payment transactions for paid services"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    request_id = db.Column(db.Integer, db.ForeignKey('emergency_requests.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False)
    
    # Payment details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='NGN')
    payment_method = db.Column(db.String(50), nullable=True)  # card, bank_transfer, mobile_money
    
    # Status tracking
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Gateway information
    gateway_reference = db.Column(db.String(100), nullable=True)
    gateway_response = db.Column(db.Text, nullable=True)  # JSON response from payment gateway
    
    # Relationships
    provider = db.relationship('Provider', backref='payments')
    
    def __init__(self, request_id, provider_id, amount, **kwargs):
        self.request_id = request_id
        self.provider_id = provider_id
        self.amount = amount
        self.transaction_id = self.generate_transaction_id()
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @staticmethod
    def generate_transaction_id():
        """Generate unique transaction ID"""
        prefix = "TXN"
        timestamp = datetime.utcnow().strftime("%y%m%d%H%M%S")
        random_part = secrets.token_hex(4).upper()
        return f"{prefix}{timestamp}{random_part}"
    
    def __repr__(self):
        return f'<Payment {self.transaction_id} ({self.status.value})>'