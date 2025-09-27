# 🔐 Security Documentation - Emergency Response USSD System

This document outlines the comprehensive security measures implemented in the Emergency Response USSD System to protect against various threats and ensure data privacy compliance.

## 🎯 Security Objectives

### Primary Goals
- **Confidentiality**: Protect sensitive user data and system information
- **Integrity**: Ensure data accuracy and prevent unauthorized modifications
- **Availability**: Maintain system uptime and prevent service disruptions
- **Accountability**: Track all system activities with comprehensive audit trails

### Compliance Standards
- **Nigeria Data Protection Regulation (NDPR)**: Data minimization and privacy
- **ISO 27001**: Information security management
- **OWASP Top 10**: Web application security best practices

## 🛡️ Threat Model & Mitigation

### 1. Tampering Attacks

**Threat**: Malicious actors sending fake or modified requests to flood the system.

**Attack Scenarios**:
- Fake SMS requests overwhelming the platform
- Modified USSD requests with malicious payloads
- Spoofed provider confirmations

**Mitigation Strategies**:
```python
# Request validation with short-lived tokens
@limiter.limit("3 per hour")
def ussd_callback():
    # Validate request signature
    if not validate_request_signature(request):
        audit_log("SECURITY_VIOLATION", "Invalid request signature")
        return "END Invalid request", 400
    
    # Rate limiting per phone number
    phone = request.form.get('phoneNumber')
    if is_rate_limited(phone):
        audit_log("RATE_LIMIT_EXCEEDED", f"Phone: {hash_phone(phone)}")
        return "END Too many requests. Please try again later.", 429
```

**Implementation Details**:
- **Rate Limiting**: Maximum 3 USSD requests per hour per phone number
- **Request Validation**: Cryptographic signature verification
- **Input Sanitization**: All user inputs validated and sanitized
- **Session Management**: Secure session tokens with expiration

### 2. Repudiation Attacks

**Threat**: Users denying they made emergency requests or received services.

**Attack Scenarios**:
- User claims they never requested shelter/food/transport
- Provider denies receiving or fulfilling a request
- Disputes over service delivery and payments

**Mitigation Strategies**:
```python
# Comprehensive audit logging
def create_emergency_request(phone, service_type, location):
    # Generate unique reference number
    reference = generate_reference_number()
    
    # Log request with encrypted phone hash
    audit_log("REQUEST_CREATED", {
        "reference": reference,
        "phone_hash": hash_phone(phone),
        "service_type": service_type,
        "location": location,
        "timestamp": datetime.utcnow(),
        "session_id": get_session_id(),
        "ip_address": get_client_ip()
    })
    
    # Send SMS confirmation with reference
    send_sms(phone, f"Request confirmed. Ref: {reference}")
    
    return reference
```

**Implementation Details**:
- **Audit Logging**: Every action logged with immutable timestamps
- **Reference Numbers**: Unique identifiers for all transactions
- **Phone Number Hashing**: Privacy-preserving user identification
- **Provider Confirmation**: Required confirmation for service delivery
- **SMS Receipts**: Automatic confirmation messages with reference numbers

### 3. Denial of Service (DoS) Attacks

**Threat**: Mass spam requests overwhelming system resources.

**Attack Scenarios**:
- Coordinated USSD request flooding
- SMS bombing through the system
- Resource exhaustion attacks

**Mitigation Strategies**:
```python
# Multi-layer rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# USSD-specific rate limiting
@limiter.limit("3 per hour")
@limiter.limit("10 per day")
def ussd_callback():
    # Additional phone-based rate limiting
    phone = request.form.get('phoneNumber')
    if redis_client.get(f"rate_limit:{phone}"):
        return "END Service temporarily unavailable. Please try again later."
    
    # Set rate limit flag
    redis_client.setex(f"rate_limit:{phone}", 3600, "1")  # 1 hour
```

**Implementation Details**:
- **Rate Limiting**: Multiple layers (IP, phone number, session)
- **Resource Monitoring**: CPU, memory, and database connection limits
- **Circuit Breakers**: Automatic service degradation under load
- **Load Balancing**: Distribute traffic across multiple instances

### 4. Privilege Escalation Attacks

**Threat**: Unauthorized users gaining admin or provider privileges.

**Attack Scenarios**:
- Unauthorized admin panel access
- Provider account takeover
- Role manipulation attacks

**Mitigation Strategies**:
```python
# Role-based access control
def require_role(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                audit_log("UNAUTHORIZED_ACCESS", f"Endpoint: {request.endpoint}")
                return jsonify({'error': 'Authentication required'}), 401
            
            if current_user.role not in roles:
                audit_log("PRIVILEGE_ESCALATION_ATTEMPT", {
                    "user_id": current_user.id,
                    "required_roles": roles,
                    "user_role": current_user.role
                })
                return jsonify({'error': 'Insufficient privileges'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Multi-factor authentication for admins
@require_role(['admin'])
@require_mfa
def admin_dashboard():
    return render_template('admin/dashboard.html')
```

**Implementation Details**:
- **Role-Based Access Control (RBAC)**: Strict role separation
- **Multi-Factor Authentication**: Required for admin accounts
- **Session Management**: Secure session handling with timeout
- **Account Lockout**: Automatic lockout after failed attempts

## 🔒 Data Protection & Privacy

### 1. Data Encryption

**At Rest**:
```python
from cryptography.fernet import Fernet

# Encrypt sensitive data before database storage
def encrypt_data(data):
    key = os.getenv('ENCRYPTION_KEY').encode()
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data):
    key = os.getenv('ENCRYPTION_KEY').encode()
    f = Fernet(key)
    return f.decrypt(encrypted_data.encode()).decode()

# Database model with encrypted fields
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_hash = db.Column(db.String(64), unique=True, nullable=False)
    encrypted_name = db.Column(db.Text)  # Encrypted PII
    
    def set_name(self, name):
        self.encrypted_name = encrypt_data(name)
    
    def get_name(self):
        return decrypt_data(self.encrypted_name) if self.encrypted_name else None
```

**In Transit**:
- **TLS 1.3**: All communications encrypted
- **Certificate Pinning**: Prevent man-in-the-middle attacks
- **HSTS Headers**: Force HTTPS connections

### 2. Data Minimization

**NDPR Compliance**:
```python
# Minimal data collection
class EmergencyRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(20), unique=True)
    phone_hash = db.Column(db.String(64))  # Hashed, not plaintext
    service_type = db.Column(db.Enum(ResourceType))
    location = db.Column(db.String(100))  # General area only
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # No storage of full names, addresses, or other PII
```

**Data Retention Policy**:
```python
# Automatic data cleanup
@app.cli.command()
def cleanup_old_data():
    retention_days = int(os.getenv('DATA_RETENTION_DAYS', 365))
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    # Delete old requests
    old_requests = EmergencyRequest.query.filter(
        EmergencyRequest.created_at < cutoff_date
    ).delete()
    
    # Delete old audit logs (separate retention period)
    audit_retention_days = int(os.getenv('AUDIT_LOG_RETENTION_DAYS', 90))
    audit_cutoff = datetime.utcnow() - timedelta(days=audit_retention_days)
    
    old_logs = AuditLog.query.filter(
        AuditLog.created_at < audit_cutoff
    ).delete()
    
    db.session.commit()
    print(f"Cleaned up {old_requests} requests and {old_logs} audit logs")
```

### 3. Privacy Protection

**Phone Number Hashing**:
```python
import hashlib

def hash_phone(phone_number):
    """Create irreversible hash of phone number for privacy"""
    salt = os.getenv('PHONE_HASH_SALT', 'default_salt')
    return hashlib.sha256(f"{phone_number}{salt}".encode()).hexdigest()

def verify_phone(phone_number, phone_hash):
    """Verify phone number against hash"""
    return hash_phone(phone_number) == phone_hash
```

**Data Sharing Controls**:
```python
# Provider data access restrictions
def get_request_for_provider(provider_id, request_id):
    request = EmergencyRequest.query.filter_by(
        id=request_id,
        resource_id=Resource.query.filter_by(provider_id=provider_id).first().id
    ).first()
    
    if request:
        # Return sanitized data only
        return {
            'reference': request.reference_number,
            'service_type': request.service_type.value,
            'location': request.location,  # General area only
            'created_at': request.created_at,
            # Phone number not included for privacy
        }
    return None
```

## 🔍 Security Monitoring & Incident Response

### 1. Real-time Monitoring

**Fraud Detection**:
```python
def detect_suspicious_activity(phone, request_data):
    """Detect potentially fraudulent requests"""
    
    # Check for rapid successive requests
    recent_requests = EmergencyRequest.query.filter(
        EmergencyRequest.phone_hash == hash_phone(phone),
        EmergencyRequest.created_at > datetime.utcnow() - timedelta(minutes=10)
    ).count()
    
    if recent_requests > 2:
        audit_log("SUSPICIOUS_ACTIVITY", {
            "phone_hash": hash_phone(phone),
            "rapid_requests": recent_requests,
            "risk_level": "HIGH"
        })
        return True
    
    # Check for unusual location patterns
    user_locations = get_user_location_history(phone)
    if is_location_anomaly(request_data['location'], user_locations):
        audit_log("LOCATION_ANOMALY", {
            "phone_hash": hash_phone(phone),
            "location": request_data['location'],
            "risk_level": "MEDIUM"
        })
    
    return False
```

**Security Alerts**:
```python
def send_security_alert(alert_type, details):
    """Send security alerts to administrators"""
    
    alert_message = f"""
    SECURITY ALERT: {alert_type}
    Time: {datetime.utcnow()}
    Details: {json.dumps(details, indent=2)}
    System: Emergency Response USSD
    """
    
    # Send to admin team
    send_email(
        to=os.getenv('SECURITY_ALERT_EMAIL'),
        subject=f"Security Alert: {alert_type}",
        body=alert_message
    )
    
    # Log to security log
    with open('/var/log/emergency-response/security.log', 'a') as f:
        f.write(f"{datetime.utcnow()}: {alert_message}\n")
```

### 2. Audit Logging

**Comprehensive Logging**:
```python
def audit_log(action, details=None, user_id=None):
    """Create immutable audit log entry"""
    
    log_entry = AuditLog(
        action=action,
        details=json.dumps(details) if details else None,
        user_id=user_id,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        timestamp=datetime.utcnow()
    )
    
    db.session.add(log_entry)
    db.session.commit()
    
    # Also log to file for backup
    log_message = f"{datetime.utcnow()}: {action} - {details}"
    app.logger.info(log_message)
```

**Log Analysis**:
```python
# Security dashboard queries
def get_security_metrics():
    """Generate security metrics for dashboard"""
    
    last_24h = datetime.utcnow() - timedelta(hours=24)
    
    metrics = {
        'failed_auth_attempts': AuditLog.query.filter(
            AuditLog.action == 'AUTHENTICATION_FAILED',
            AuditLog.timestamp > last_24h
        ).count(),
        
        'rate_limit_violations': AuditLog.query.filter(
            AuditLog.action == 'RATE_LIMIT_EXCEEDED',
            AuditLog.timestamp > last_24h
        ).count(),
        
        'suspicious_activities': AuditLog.query.filter(
            AuditLog.action == 'SUSPICIOUS_ACTIVITY',
            AuditLog.timestamp > last_24h
        ).count(),
        
        'privilege_escalation_attempts': AuditLog.query.filter(
            AuditLog.action == 'PRIVILEGE_ESCALATION_ATTEMPT',
            AuditLog.timestamp > last_24h
        ).count()
    }
    
    return metrics
```

## 🚨 Incident Response Plan

### 1. Security Incident Classification

**Severity Levels**:
- **Critical**: System compromise, data breach, service unavailable
- **High**: Privilege escalation, persistent attacks, data integrity issues
- **Medium**: Failed authentication attempts, suspicious activities
- **Low**: Rate limiting triggers, minor configuration issues

### 2. Response Procedures

**Immediate Response** (0-15 minutes):
1. **Detect**: Automated monitoring alerts
2. **Assess**: Determine severity and impact
3. **Contain**: Isolate affected systems if necessary
4. **Notify**: Alert security team and stakeholders

**Investigation** (15 minutes - 2 hours):
1. **Analyze**: Review audit logs and system metrics
2. **Document**: Record all findings and actions taken
3. **Preserve**: Maintain evidence for forensic analysis

**Recovery** (2-24 hours):
1. **Remediate**: Fix vulnerabilities and restore services
2. **Monitor**: Enhanced monitoring for recurring issues
3. **Communicate**: Update stakeholders on resolution

### 3. Contact Information

**Security Team**:
- **Primary**: security@emergency-response.ng
- **Emergency**: +234-XXX-XXX-XXXX
- **Escalation**: CTO/Security Officer

## 📋 Security Checklist

### Pre-Deployment
- [ ] All secrets stored in environment variables
- [ ] Database connections encrypted
- [ ] SSL/TLS certificates configured
- [ ] Rate limiting implemented
- [ ] Input validation in place
- [ ] Audit logging enabled
- [ ] Security headers configured
- [ ] Firewall rules applied

### Post-Deployment
- [ ] Security monitoring active
- [ ] Backup procedures tested
- [ ] Incident response plan reviewed
- [ ] Security training completed
- [ ] Vulnerability scanning scheduled
- [ ] Compliance audit passed

### Ongoing Maintenance
- [ ] Regular security updates
- [ ] Log analysis and review
- [ ] Access control audits
- [ ] Penetration testing
- [ ] Security awareness training
- [ ] Disaster recovery testing

## 📚 Security Resources

### Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Nigeria Data Protection Regulation](https://ndpr.gov.ng/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.0.x/security/)

### Tools
- **Static Analysis**: Bandit, Safety
- **Dependency Scanning**: pip-audit
- **Penetration Testing**: OWASP ZAP, Burp Suite
- **Monitoring**: ELK Stack, Prometheus

---

**Security is everyone's responsibility. Stay vigilant! 🛡️**