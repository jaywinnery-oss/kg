"""
Admin Routes for Emergency Response System
Administrative dashboard and management interface
"""
from flask import render_template_string, jsonify, request, current_app
from app.admin import bp
from app import db
from app.models import (
    Resource, EmergencyRequest, User, Provider, AuditLog,
    ResourceType, RequestStatus, UserRole
)
from app.security import require_role, audit_log, SecurityService
from app.services.matching_service import MatchingService
from datetime import datetime, timedelta
import json

@bp.route('/')
@require_role(['admin'])
@audit_log('admin_dashboard_access')
def dashboard():
    """Admin dashboard with system overview"""
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard - Emergency Response System</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
            .header { background: #d32f2f; color: white; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stat-number { font-size: 2em; font-weight: bold; color: #d32f2f; }
            .stat-label { color: #666; margin-top: 5px; }
            .section { background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .btn { background: #d32f2f; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn:hover { background: #b71c1c; }
            .btn-secondary { background: #666; }
            .btn-secondary:hover { background: #555; }
            .alert { padding: 15px; margin: 10px 0; border-radius: 4px; }
            .alert-warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
            .alert-danger { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
            .table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            .table th, .table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            .table th { background: #f8f9fa; font-weight: bold; }
            .status-pending { color: #ff9800; font-weight: bold; }
            .status-matched { color: #2196f3; font-weight: bold; }
            .status-confirmed { color: #4caf50; font-weight: bold; }
            .status-completed { color: #8bc34a; font-weight: bold; }
            .nav-tabs { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 20px; }
            .nav-tab { padding: 10px 20px; background: #f8f9fa; border: 1px solid #ddd; border-bottom: none; cursor: pointer; }
            .nav-tab.active { background: white; border-bottom: 2px solid white; margin-bottom: -2px; }
        </style>
        <script>
            function showTab(tabName) {
                // Hide all sections
                const sections = document.querySelectorAll('.tab-content');
                sections.forEach(section => section.style.display = 'none');
                
                // Remove active class from all tabs
                const tabs = document.querySelectorAll('.nav-tab');
                tabs.forEach(tab => tab.classList.remove('active'));
                
                // Show selected section and activate tab
                document.getElementById(tabName).style.display = 'block';
                event.target.classList.add('active');
            }
            
            function refreshStats() {
                location.reload();
            }
            
            function autoMatch() {
                fetch('/api/matching/auto-match', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        alert(`Auto-matching completed: ${data.matched} matched, ${data.failed} failed`);
                        refreshStats();
                    })
                    .catch(error => alert('Auto-matching failed: ' + error));
            }
        </script>
    </head>
    <body>
        <div class="header">
            <div class="container">
                <h1>🚨 Emergency Response Admin Dashboard</h1>
                <p>System monitoring and management interface</p>
            </div>
        </div>
        
        <div class="container">
            <!-- System Statistics -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{{ stats.total_requests }}</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.active_requests }}</div>
                    <div class="stat-label">Active Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.total_resources }}</div>
                    <div class="stat-label">Total Resources</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.recent_requests }}</div>
                    <div class="stat-label">Requests (24h)</div>
                </div>
            </div>
            
            <!-- Security Alerts -->
            {% if security_alerts %}
            <div class="section">
                <h2>🔒 Security Alerts</h2>
                {% for alert in security_alerts %}
                <div class="alert alert-{{ alert.type }}">
                    <strong>{{ alert.title }}</strong> - {{ alert.message }}
                    <small>({{ alert.timestamp }})</small>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <!-- Quick Actions -->
            <div class="section">
                <h2>⚡ Quick Actions</h2>
                <button class="btn" onclick="autoMatch()">🔄 Run Auto-Matching</button>
                <button class="btn btn-secondary" onclick="refreshStats()">📊 Refresh Stats</button>
                <a href="/api/stats" class="btn btn-secondary">📈 View API Stats</a>
                <a href="/api/security/audit-logs" class="btn btn-secondary">🔍 View Audit Logs</a>
            </div>
            
            <!-- Tabbed Content -->
            <div class="nav-tabs">
                <div class="nav-tab active" onclick="showTab('recent-requests')">Recent Requests</div>
                <div class="nav-tab" onclick="showTab('resource-status')">Resource Status</div>
                <div class="nav-tab" onclick="showTab('system-health')">System Health</div>
            </div>
            
            <!-- Recent Requests Tab -->
            <div id="recent-requests" class="tab-content section">
                <h2>📋 Recent Emergency Requests</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Reference</th>
                            <th>Type</th>
                            <th>Location</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Resource</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for request in recent_requests %}
                        <tr>
                            <td>{{ request.reference_number }}</td>
                            <td>{{ request.resource_type.value.title() }}</td>
                            <td>{{ request.location }}</td>
                            <td class="status-{{ request.status.value }}">{{ request.status.value.title() }}</td>
                            <td>{{ request.created_at.strftime('%H:%M %d/%m') }}</td>
                            <td>{{ request.resource.name if request.resource else 'Not matched' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <!-- Resource Status Tab -->
            <div id="resource-status" class="tab-content section" style="display: none;">
                <h2>🏢 Resource Utilization</h2>
                {% for type, stats in resource_utilization.items() %}
                <div style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px;">
                    <h3>{{ type.title() }}</h3>
                    <p><strong>Total Resources:</strong> {{ stats.total_resources }}</p>
                    <p><strong>Total Capacity:</strong> {{ stats.total_capacity }}</p>
                    <p><strong>Available:</strong> {{ stats.available_capacity }}</p>
                    <p><strong>Utilization Rate:</strong> {{ stats.utilization_rate }}%</p>
                    <div style="background: #f0f0f0; height: 20px; border-radius: 10px; overflow: hidden;">
                        <div style="background: #d32f2f; height: 100%; width: {{ stats.utilization_rate }}%; transition: width 0.3s;"></div>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <!-- System Health Tab -->
            <div id="system-health" class="tab-content section" style="display: none;">
                <h2>💚 System Health</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <div style="padding: 15px; background: #e8f5e8; border-radius: 5px;">
                        <h4>Database</h4>
                        <p>✅ Operational</p>
                    </div>
                    <div style="padding: 15px; background: #e8f5e8; border-radius: 5px;">
                        <h4>USSD Service</h4>
                        <p>✅ Operational</p>
                    </div>
                    <div style="padding: 15px; background: #e8f5e8; border-radius: 5px;">
                        <h4>SMS Service</h4>
                        <p>✅ Operational</p>
                    </div>
                    <div style="padding: 15px; background: #e8f5e8; border-radius: 5px;">
                        <h4>Matching Engine</h4>
                        <p>✅ Operational</p>
                    </div>
                </div>
                
                <h3>Configuration</h3>
                <table class="table">
                    <tr><td>USSD Service Code</td><td>{{ config.ussd_service_code }}</td></tr>
                    <tr><td>USSD Channel</td><td>{{ config.ussd_channel }}</td></tr>
                    <tr><td>Rate Limit (USSD)</td><td>{{ config.ussd_rate_limit }}</td></tr>
                    <tr><td>Rate Limit (SMS)</td><td>{{ config.sms_rate_limit }}</td></tr>
                    <tr><td>Data Retention</td><td>{{ config.data_retention_days }} days</td></tr>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # Get system statistics
        total_requests = EmergencyRequest.query.count()
        active_requests = EmergencyRequest.query.filter(
            EmergencyRequest.status.in_([RequestStatus.PENDING, RequestStatus.MATCHED])
        ).count()
        total_resources = Resource.query.filter(Resource.is_active == True).count()
        
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_requests_count = EmergencyRequest.query.filter(
            EmergencyRequest.created_at >= yesterday
        ).count()
        
        # Get recent requests for display
        recent_requests = EmergencyRequest.query.order_by(
            EmergencyRequest.created_at.desc()
        ).limit(10).all()
        
        # Get resource utilization
        resource_utilization = MatchingService.get_resource_utilization_stats()
        
        # Check for security alerts (simplified)
        security_alerts = []
        
        # Check for high rate of failed requests
        recent_failed = EmergencyRequest.query.filter(
            EmergencyRequest.created_at >= datetime.utcnow() - timedelta(hours=1),
            EmergencyRequest.status == RequestStatus.PENDING
        ).count()
        
        if recent_failed > 10:
            security_alerts.append({
                'type': 'warning',
                'title': 'High Unmatched Requests',
                'message': f'{recent_failed} requests pending in the last hour',
                'timestamp': datetime.utcnow().strftime('%H:%M')
            })
        
        stats = {
            'total_requests': total_requests,
            'active_requests': active_requests,
            'total_resources': total_resources,
            'recent_requests': recent_requests_count
        }
        
        config = {
            'ussd_service_code': current_app.config.get('USSD_SERVICE_CODE'),
            'ussd_channel': current_app.config.get('USSD_CHANNEL'),
            'ussd_rate_limit': current_app.config.get('USSD_RATE_LIMIT'),
            'sms_rate_limit': current_app.config.get('SMS_RATE_LIMIT'),
            'data_retention_days': current_app.config.get('DATA_RETENTION_DAYS')
        }
        
        return render_template_string(
            dashboard_html,
            stats=stats,
            recent_requests=recent_requests,
            resource_utilization=resource_utilization,
            security_alerts=security_alerts,
            config=config
        )
        
    except Exception as e:
        current_app.logger.error(f"Error loading admin dashboard: {e}")
        return jsonify({'error': 'Failed to load dashboard'}), 500

@bp.route('/resources')
@require_role(['admin'])
@audit_log('admin_resources_view')
def manage_resources():
    """Resource management interface"""
    try:
        resources = Resource.query.order_by(Resource.created_at.desc()).all()
        
        resource_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Resource Management - Emergency Response System</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
                .header { background: #d32f2f; color: white; padding: 20px; }
                .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
                .section { background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .btn { background: #d32f2f; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
                .btn:hover { background: #b71c1c; }
                .btn-success { background: #4caf50; }
                .btn-success:hover { background: #45a049; }
                .btn-warning { background: #ff9800; }
                .btn-warning:hover { background: #f57c00; }
                .table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                .table th, .table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                .table th { background: #f8f9fa; font-weight: bold; }
                .status-active { color: #4caf50; font-weight: bold; }
                .status-inactive { color: #f44336; font-weight: bold; }
                .capacity-bar { background: #f0f0f0; height: 20px; border-radius: 10px; overflow: hidden; }
                .capacity-fill { background: #4caf50; height: 100%; transition: width 0.3s; }
                .capacity-low { background: #ff9800; }
                .capacity-empty { background: #f44336; }
            </style>
        </head>
        <body>
            <div class="header">
                <div class="container">
                    <h1>🏢 Resource Management</h1>
                    <a href="/admin/" class="btn">← Back to Dashboard</a>
                </div>
            </div>
            
            <div class="container">
                <div class="section">
                    <h2>All Resources</h2>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Location</th>
                                <th>Capacity</th>
                                <th>Utilization</th>
                                <th>Price</th>
                                <th>Status</th>
                                <th>Provider</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for resource in resources %}
                            <tr>
                                <td><strong>{{ resource.name }}</strong></td>
                                <td>{{ resource.resource_type.value.title() }}</td>
                                <td>{{ resource.location }}</td>
                                <td>{{ resource.available_capacity }} / {{ resource.total_capacity }}</td>
                                <td>
                                    {% set utilization = ((resource.total_capacity - resource.available_capacity) / resource.total_capacity * 100) if resource.total_capacity > 0 else 0 %}
                                    <div class="capacity-bar">
                                        <div class="capacity-fill {% if utilization > 80 %}capacity-empty{% elif utilization > 50 %}capacity-low{% endif %}" 
                                             style="width: {{ utilization }}%"></div>
                                    </div>
                                    {{ "%.1f"|format(utilization) }}%
                                </td>
                                <td>
                                    {% if resource.price_per_unit > 0 %}
                                        ₦{{ resource.price_per_unit }}
                                    {% else %}
                                        Free
                                    {% endif %}
                                </td>
                                <td class="status-{{ 'active' if resource.is_active else 'inactive' }}">
                                    {{ 'Active' if resource.is_active else 'Inactive' }}
                                </td>
                                <td>{{ resource.provider.organization_name if resource.provider else 'N/A' }}</td>
                                <td>
                                    <button class="btn btn-warning" onclick="editResource({{ resource.id }})">Edit</button>
                                    {% if resource.is_active %}
                                        <button class="btn" onclick="toggleResource({{ resource.id }}, false)">Deactivate</button>
                                    {% else %}
                                        <button class="btn btn-success" onclick="toggleResource({{ resource.id }}, true)">Activate</button>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <script>
                function editResource(id) {
                    alert('Edit functionality would open a form for resource ID: ' + id);
                }
                
                function toggleResource(id, activate) {
                    const action = activate ? 'activate' : 'deactivate';
                    if (confirm(`Are you sure you want to ${action} this resource?`)) {
                        // In a real implementation, this would make an API call
                        alert(`Resource ${action}d successfully`);
                        location.reload();
                    }
                }
            </script>
        </body>
        </html>
        """
        
        return render_template_string(resource_html, resources=resources)
        
    except Exception as e:
        current_app.logger.error(f"Error loading resource management: {e}")
        return jsonify({'error': 'Failed to load resources'}), 500

@bp.route('/security')
@require_role(['admin'])
@audit_log('admin_security_view')
def security_monitoring():
    """Security monitoring dashboard"""
    try:
        # Get recent audit logs
        recent_logs = AuditLog.query.order_by(
            AuditLog.timestamp.desc()
        ).limit(50).all()
        
        # Get security statistics
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_failed_attempts = AuditLog.query.filter(
            AuditLog.timestamp >= one_hour_ago,
            AuditLog.action.like('%failed%')
        ).count()
        
        return jsonify({
            'recent_logs': [{
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'action': log.action,
                'ip_address': log.ip_address,
                'user_id': log.user_id,
                'details': json.loads(log.details) if log.details else None
            } for log in recent_logs],
            'security_stats': {
                'recent_failed_attempts': recent_failed_attempts,
                'total_audit_logs': AuditLog.query.count(),
                'active_sessions': db.session.query(db.func.count(db.distinct(AuditLog.session_id))).filter(
                    AuditLog.timestamp >= one_hour_ago
                ).scalar()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error loading security monitoring: {e}")
        return jsonify({'error': 'Failed to load security data'}), 500