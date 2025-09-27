"""
Main Routes for Emergency Response System
Core application routes and landing pages
"""
from flask import render_template_string, jsonify, current_app
from app.main import bp
from app.models import Resource, EmergencyRequest, ResourceType, RequestStatus
from app.services.matching_service import MatchingService
from datetime import datetime, timedelta

@bp.route('/')
def index():
    """Main landing page with system overview"""
    try:
        # Get basic statistics
        total_resources = Resource.query.filter(Resource.is_active == True).count()
        total_requests = EmergencyRequest.query.count()
        active_requests = EmergencyRequest.query.filter(
            EmergencyRequest.status.in_([RequestStatus.PENDING, RequestStatus.MATCHED])
        ).count()
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_requests = EmergencyRequest.query.filter(
            EmergencyRequest.created_at >= yesterday
        ).count()
        
        return jsonify({
            'message': '🚨 Emergency Response USSD System',
            'description': 'Connecting disaster victims to life-saving resources through basic mobile phones',
            'version': '1.0.0',
            'status': 'operational',
            'statistics': {
                'total_resources': total_resources,
                'total_requests': total_requests,
                'active_requests': active_requests,
                'recent_requests_24h': recent_requests
            },
            'endpoints': {
                'ussd_callback': '/ussd/callback',
                'ussd_test': '/ussd/test',
                'api_resources': '/api/resources',
                'api_requests': '/api/requests',
                'api_stats': '/api/stats',
                'admin_dashboard': '/admin/',
                'provider_portal': '/provider/'
            },
            'ussd_service': {
                'service_code': current_app.config.get('USSD_SERVICE_CODE', '*384#'),
                'channel': current_app.config.get('USSD_CHANNEL', '17925'),
                'instructions': 'Dial *384# from any mobile phone to access emergency services'
            },
            'security_features': [
                'Rate limiting and abuse prevention',
                'Data encryption and privacy protection',
                'Audit logging and monitoring',
                'Request validation and fraud detection',
                'Role-based access control'
            ],
            'supported_services': [
                {'type': 'shelter', 'description': 'Emergency accommodation and safe spaces'},
                {'type': 'food', 'description': 'Food distribution and emergency meals'},
                {'type': 'transport', 'description': 'Evacuation and medical transport services'}
            ]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in index route: {e}")
        return jsonify({
            'message': 'Emergency Response USSD System',
            'status': 'error',
            'error': 'Unable to load system statistics'
        }), 500

@bp.route('/privacy')
def privacy_policy():
    """Privacy policy for NDPR compliance"""
    privacy_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Privacy Policy - Emergency Response System</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            h1, h2 { color: #d32f2f; }
            .container { max-width: 800px; margin: 0 auto; }
            .highlight { background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔒 Privacy Policy</h1>
            <p><strong>Emergency Response USSD System</strong></p>
            <p><em>Last updated: {{ date }}</em></p>
            
            <div class="highlight">
                <p><strong>NDPR Compliance Notice:</strong> This system complies with the Nigeria Data Protection Regulation (NDPR) 2019.</p>
            </div>
            
            <h2>1. Data We Collect</h2>
            <p>We collect minimal data necessary for emergency response:</p>
            <ul>
                <li><strong>Phone Number:</strong> To identify and contact you (encrypted and hashed)</li>
                <li><strong>Location:</strong> To match you with nearby resources</li>
                <li><strong>Service Type:</strong> To understand your emergency needs</li>
                <li><strong>Request History:</strong> To prevent fraud and improve services</li>
            </ul>
            
            <h2>2. How We Use Your Data</h2>
            <ul>
                <li>Connect you with emergency resources</li>
                <li>Send SMS confirmations and updates</li>
                <li>Prevent fraud and abuse</li>
                <li>Improve our services</li>
                <li>Comply with legal requirements</li>
            </ul>
            
            <h2>3. Data Protection</h2>
            <ul>
                <li><strong>Encryption:</strong> All sensitive data is encrypted</li>
                <li><strong>Hashing:</strong> Phone numbers are hashed for privacy</li>
                <li><strong>Access Control:</strong> Role-based access to data</li>
                <li><strong>Audit Logging:</strong> All access is logged and monitored</li>
                <li><strong>Retention:</strong> Data is deleted after {{ retention_days }} days</li>
            </ul>
            
            <h2>4. Data Sharing</h2>
            <p>We only share data with:</p>
            <ul>
                <li>Emergency service providers (minimal necessary information)</li>
                <li>Government agencies (for emergency coordination)</li>
                <li>Law enforcement (when legally required)</li>
            </ul>
            
            <h2>5. Your Rights</h2>
            <p>Under NDPR, you have the right to:</p>
            <ul>
                <li>Access your personal data</li>
                <li>Correct inaccurate data</li>
                <li>Delete your data (subject to legal requirements)</li>
                <li>Object to data processing</li>
                <li>Data portability</li>
            </ul>
            
            <h2>6. Contact Us</h2>
            <p>For privacy concerns or data requests:</p>
            <ul>
                <li><strong>Email:</strong> privacy@emergency-response.ng</li>
                <li><strong>Phone:</strong> +234-XXX-XXX-XXXX</li>
                <li><strong>Address:</strong> [Your Address]</li>
            </ul>
            
            <h2>7. Changes to This Policy</h2>
            <p>We may update this policy. Changes will be posted here with the updated date.</p>
            
            <p><em>This policy is effective as of the date shown above.</em></p>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(
        privacy_html,
        date=datetime.utcnow().strftime('%B %d, %Y'),
        retention_days=current_app.config.get('DATA_RETENTION_DAYS', 365)
    )

@bp.route('/status')
def system_status():
    """System status and health information"""
    try:
        # Check database connectivity
        db_status = 'healthy'
        try:
            Resource.query.first()
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        # Check recent activity
        recent_requests = EmergencyRequest.query.filter(
            EmergencyRequest.created_at >= datetime.utcnow() - timedelta(minutes=5)
        ).count()
        
        # Get resource availability
        resource_stats = MatchingService.get_resource_utilization_stats()
        
        return jsonify({
            'status': 'operational',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': db_status,
                'ussd_service': 'operational',
                'sms_service': 'operational',
                'matching_engine': 'operational'
            },
            'metrics': {
                'recent_requests_5min': recent_requests,
                'resource_utilization': resource_stats
            },
            'configuration': {
                'ussd_service_code': current_app.config.get('USSD_SERVICE_CODE'),
                'ussd_channel': current_app.config.get('USSD_CHANNEL'),
                'rate_limits': {
                    'ussd': current_app.config.get('USSD_RATE_LIMIT'),
                    'sms': current_app.config.get('SMS_RATE_LIMIT')
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in status check: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@bp.route('/docs')
def api_documentation():
    """API documentation"""
    docs_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Documentation - Emergency Response System</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            h1, h2, h3 { color: #d32f2f; }
            .container { max-width: 1000px; margin: 0 auto; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { display: inline-block; padding: 3px 8px; border-radius: 3px; color: white; font-weight: bold; }
            .get { background: #4caf50; }
            .post { background: #2196f3; }
            .put { background: #ff9800; }
            .delete { background: #f44336; }
            code { background: #e8e8e8; padding: 2px 4px; border-radius: 3px; }
            pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📚 API Documentation</h1>
            <p><strong>Emergency Response USSD System API</strong></p>
            
            <h2>Authentication</h2>
            <p>Most endpoints require role-based authentication. Include appropriate credentials in your requests.</p>
            
            <h2>Rate Limits</h2>
            <ul>
                <li>General API: 100 requests per hour</li>
                <li>USSD endpoints: 3 requests per hour per phone number</li>
                <li>Resource creation: 10 requests per hour</li>
            </ul>
            
            <h2>Core Endpoints</h2>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/health</h3>
                <p>Health check endpoint</p>
                <pre>Response: {"status": "healthy", "timestamp": "2024-01-01T00:00:00"}</pre>
            </div>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/resources</h3>
                <p>List all resources with optional filtering</p>
                <p><strong>Parameters:</strong></p>
                <ul>
                    <li><code>type</code> - Resource type (shelter, food, transport)</li>
                    <li><code>location</code> - Location filter</li>
                    <li><code>available_only</code> - Show only available resources</li>
                    <li><code>page</code> - Page number</li>
                    <li><code>per_page</code> - Items per page (max 100)</li>
                </ul>
            </div>
            
            <div class="endpoint">
                <h3><span class="method post">POST</span> /api/resources</h3>
                <p>Create a new resource (requires NGO/Government/Admin role)</p>
                <p><strong>Required fields:</strong> name, type, location, total_capacity, provider_id</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/requests</h3>
                <p>List emergency requests (requires elevated permissions)</p>
                <p><strong>Parameters:</strong> status, type, location, date_from, date_to, page, per_page</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method post">POST</span> /api/requests/{reference_number}/confirm</h3>
                <p>Confirm service delivery for a request</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/stats</h3>
                <p>Get system statistics</p>
                <p><strong>Parameters:</strong> days (default: 7)</p>
            </div>
            
            <h2>USSD Endpoints</h2>
            
            <div class="endpoint">
                <h3><span class="method post">POST</span> /ussd/callback</h3>
                <p>Main USSD callback for Africa's Talking integration</p>
                <p><strong>Required fields:</strong> sessionId, phoneNumber, text</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method post">POST</span> /ussd/test</h3>
                <p>Test USSD functionality (development only)</p>
            </div>
            
            <h2>Security Features</h2>
            <ul>
                <li><strong>Rate Limiting:</strong> Prevents abuse and DoS attacks</li>
                <li><strong>Request Validation:</strong> All inputs are validated</li>
                <li><strong>Audit Logging:</strong> All actions are logged</li>
                <li><strong>Data Encryption:</strong> Sensitive data is encrypted</li>
                <li><strong>Role-based Access:</strong> Different permission levels</li>
            </ul>
            
            <h2>Error Responses</h2>
            <p>All errors return JSON with error details:</p>
            <pre>{"error": "Error type", "message": "Detailed error message"}</pre>
            
            <h2>Contact</h2>
            <p>For API support: <strong>api-support@emergency-response.ng</strong></p>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(docs_html)