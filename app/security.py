"""
Security utilities and services for the Emergency Response System
Includes rate limiting, request validation, audit logging, and fraud detection
"""
from functools import wraps
from flask import request, jsonify, current_app, g
from app import db, limiter
from app.models import User, AuditLog, USSDSession
from datetime import datetime, timedelta
import re
import hashlib
import hmac
import secrets
import json

class SecurityService:
    """Centralized security service for validation and monitoring"""
    
    @staticmethod
    def validate_phone_number(phone_number):
        """Validate Nigerian phone number format"""
        if not phone_number:
            return False
        
        # Remove any non-digit characters
        clean_phone = re.sub(r'\D', '', phone_number)
        
        # Nigerian phone number patterns
        patterns = [
            r'^234[789][01]\d{8}$',  # +234 format
            r'^0[789][01]\d{8}$',    # 0 prefix format
            r'^[789][01]\d{8}$'      # Without prefix
        ]
        
        for pattern in patterns:
            if re.match(pattern, clean_phone):
                return True
        return False
    
    @staticmethod
    def normalize_phone_number(phone_number):
        """Normalize phone number to standard format"""
        if not phone_number:
            return None
        
        clean_phone = re.sub(r'\D', '', phone_number)
        
        # Convert to +234 format
        if clean_phone.startswith('234'):
            return f"+{clean_phone}"
        elif clean_phone.startswith('0'):
            return f"+234{clean_phone[1:]}"
        elif len(clean_phone) == 10:
            return f"+234{clean_phone}"
        
        return phone_number  # Return as-is if can't normalize
    
    @staticmethod
    def validate_ussd_request(data):
        """Validate USSD request from Africa's Talking"""
        required_fields = ['sessionId', 'phoneNumber', 'text']
        
        if not isinstance(data, dict):
            return False, "Invalid request format"
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate phone number
        if not SecurityService.validate_phone_number(data['phoneNumber']):
            return False, "Invalid phone number format"
        
        # Validate session ID format
        if not re.match(r'^[a-zA-Z0-9_-]+$', data['sessionId']):
            return False, "Invalid session ID format"
        
        return True, "Valid request"
    
    @staticmethod
    def validate_sms_request(data):
        """Validate SMS request"""
        required_fields = ['to', 'message']
        
        if not isinstance(data, dict):
            return False, "Invalid request format"
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate phone number
        if not SecurityService.validate_phone_number(data['to']):
            return False, "Invalid phone number format"
        
        # Validate message length
        if len(data['message']) > 160:
            return False, "Message too long (max 160 characters)"
        
        return True, "Valid request"
    
    @staticmethod
    def detect_suspicious_activity(user_id, action_type, details=None):
        """Detect suspicious activity patterns"""
        if not user_id:
            return False
        
        # Check for rapid successive requests
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        recent_actions = AuditLog.query.filter(
            AuditLog.user_id == user_id,
            AuditLog.action == action_type,
            AuditLog.timestamp > five_minutes_ago
        ).count()
        
        if recent_actions > 5:  # More than 5 actions in 5 minutes
            return True
        
        # Check for requests from multiple locations (if location data available)
        if details and 'location' in details:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_locations = db.session.query(AuditLog.details).filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp > one_hour_ago,
                AuditLog.details.isnot(None)
            ).all()
            
            unique_locations = set()
            for log in recent_locations:
                try:
                    log_details = json.loads(log.details)
                    if 'location' in log_details:
                        unique_locations.add(log_details['location'])
                except:
                    continue
            
            if len(unique_locations) > 3:  # Requests from more than 3 locations in 1 hour
                return True
        
        return False
    
    @staticmethod
    def log_security_event(event_type, details, severity='INFO'):
        """Log security events for monitoring"""
        current_app.logger.log(
            getattr(current_app.logger, severity.lower(), current_app.logger.info),
            f"SECURITY_EVENT: {event_type} - {details}"
        )

def audit_log(action, resource_type=None, resource_id=None, details=None):
    """Decorator to automatically log actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the function first
            result = f(*args, **kwargs)
            
            # Log the action
            try:
                user_id = getattr(g, 'current_user_id', None)
                session_id = getattr(g, 'session_id', None)
                
                log_entry = AuditLog(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    details=json.dumps(details) if details else None,
                    session_id=session_id
                )
                
                db.session.add(log_entry)
                db.session.commit()
                
            except Exception as e:
                current_app.logger.error(f"Failed to create audit log: {e}")
            
            return result
        return decorated_function
    return decorator

def rate_limit_by_phone(limit="3 per hour"):
    """Rate limiting decorator based on phone number"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract phone number from request
            phone_number = None
            if request.is_json:
                phone_number = request.json.get('phoneNumber')
            else:
                phone_number = request.form.get('phoneNumber')
            
            if phone_number:
                # Use phone number as key for rate limiting
                key = f"phone:{hashlib.md5(phone_number.encode()).hexdigest()}"
                
                # Apply rate limit
                try:
                    limiter.limit(limit, key_func=lambda: key)
                except Exception as e:
                    current_app.logger.warning(f"Rate limit exceeded for phone {phone_number[:4]}****")
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': 'Too many requests from this phone number'
                    }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_request_signature(secret_key):
    """Validate request signature from Africa's Talking"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config.get('TESTING'):  # Skip in testing
                signature = request.headers.get('X-Signature')
                if not signature:
                    return jsonify({'error': 'Missing signature'}), 401
                
                # Calculate expected signature
                body = request.get_data()
                expected_signature = hmac.new(
                    secret_key.encode(),
                    body,
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(signature, expected_signature):
                    SecurityService.log_security_event(
                        'INVALID_SIGNATURE',
                        f'Invalid signature from {request.remote_addr}',
                        'WARNING'
                    )
                    return jsonify({'error': 'Invalid signature'}), 401
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(required_roles):
    """Require specific user roles"""
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = getattr(g, 'current_user_id', None)
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            user = User.query.get(user_id)
            if not user or user.role.value not in required_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def session_required(f):
    """Require valid USSD session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.json.get('sessionId') if request.is_json else request.form.get('sessionId')
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        session = USSDSession.query.filter_by(session_id=session_id).first()
        if not session or session.is_expired():
            return jsonify({'error': 'Invalid or expired session'}), 401
        
        # Store session info in g for use in the view
        g.current_session = session
        g.current_user_id = session.user_id
        g.session_id = session_id
        
        # Extend session
        session.extend_session()
        db.session.commit()
        
        return f(*args, **kwargs)
    return decorated_function

class FraudDetection:
    """Fraud detection and prevention system"""
    
    @staticmethod
    def check_duplicate_requests(user_id, resource_type, location, time_window_minutes=30):
        """Check for duplicate requests within time window"""
        from app.models import EmergencyRequest, RequestStatus
        
        time_threshold = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        duplicate = EmergencyRequest.query.filter(
            EmergencyRequest.user_id == user_id,
            EmergencyRequest.resource_type == resource_type,
            EmergencyRequest.location == location,
            EmergencyRequest.created_at > time_threshold,
            EmergencyRequest.status != RequestStatus.CANCELLED
        ).first()
        
        return duplicate is not None
    
    @staticmethod
    def check_provider_capacity_fraud(resource_id, requested_quantity):
        """Check if provider is claiming false capacity"""
        from app.models import Resource
        
        resource = Resource.query.get(resource_id)
        if not resource:
            return True  # Resource doesn't exist
        
        # Check if requested quantity exceeds available capacity
        if requested_quantity > resource.available_capacity:
            return True
        
        # Check if capacity updates are suspicious (e.g., capacity increasing without explanation)
        # This would require additional tracking of capacity changes
        
        return False
    
    @staticmethod
    def analyze_request_patterns(user_id):
        """Analyze user request patterns for anomalies"""
        from app.models import EmergencyRequest
        
        # Get user's request history
        requests = EmergencyRequest.query.filter_by(user_id=user_id).order_by(
            EmergencyRequest.created_at.desc()
        ).limit(10).all()
        
        if len(requests) < 3:
            return False  # Not enough data
        
        # Check for rapid successive requests
        time_diffs = []
        for i in range(1, len(requests)):
            diff = (requests[i-1].created_at - requests[i].created_at).total_seconds() / 60
            time_diffs.append(diff)
        
        # If average time between requests is less than 10 minutes, flag as suspicious
        avg_time_diff = sum(time_diffs) / len(time_diffs)
        if avg_time_diff < 10:
            return True
        
        # Check for requests from too many different locations
        locations = set(req.location for req in requests)
        if len(locations) > 5:  # More than 5 different locations
            return True
        
        return False

def cleanup_expired_sessions():
    """Clean up expired USSD sessions"""
    expired_sessions = USSDSession.query.filter(
        USSDSession.expires_at < datetime.utcnow()
    ).all()
    
    for session in expired_sessions:
        db.session.delete(session)
    
    db.session.commit()
    return len(expired_sessions)

def cleanup_old_audit_logs(retention_days=90):
    """Clean up old audit logs based on retention policy"""
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    old_logs = AuditLog.query.filter(
        AuditLog.timestamp < cutoff_date
    ).all()
    
    for log in old_logs:
        db.session.delete(log)
    
    db.session.commit()
    return len(old_logs)