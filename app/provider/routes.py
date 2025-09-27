"""
Provider Routes for Emergency Response System
Service provider portal for managing resources and earnings
"""
from flask import render_template_string, jsonify, request, current_app
from app.provider import bp
from app import db
from app.models import (
    Provider, Resource, EmergencyRequest, Payment, 
    ResourceType, RequestStatus, PaymentStatus
)
from app.security import require_role, audit_log
from datetime import datetime, timedelta

@bp.route('/')
@require_role(['ngo', 'government', 'volunteer'])
@audit_log('provider_dashboard_access')
def dashboard():
    """Provider dashboard"""
    provider_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Provider Portal - Emergency Response System</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
            .header { background: #2196f3; color: white; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
            .stat-number { font-size: 2em; font-weight: bold; color: #2196f3; }
            .stat-label { color: #666; margin-top: 5px; }
            .section { background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .btn { background: #2196f3; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
            .btn:hover { background: #1976d2; }
            .btn-success { background: #4caf50; }
            .btn-success:hover { background: #45a049; }
            .table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            .table th, .table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            .table th { background: #f8f9fa; font-weight: bold; }
            .status-pending { color: #ff9800; font-weight: bold; }
            .status-matched { color: #2196f3; font-weight: bold; }
            .status-confirmed { color: #4caf50; font-weight: bold; }
            .nav-tabs { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 20px; }
            .nav-tab { padding: 10px 20px; background: #f8f9fa; border: 1px solid #ddd; border-bottom: none; cursor: pointer; }
            .nav-tab.active { background: white; border-bottom: 2px solid white; margin-bottom: -2px; }
        </style>
        <script>
            function showTab(tabName) {
                const sections = document.querySelectorAll('.tab-content');
                sections.forEach(section => section.style.display = 'none');
                
                const tabs = document.querySelectorAll('.nav-tab');
                tabs.forEach(tab => tab.classList.remove('active'));
                
                document.getElementById(tabName).style.display = 'block';
                event.target.classList.add('active');
            }
            
            function confirmRequest(referenceNumber) {
                if (confirm('Confirm that you have provided the service for request ' + referenceNumber + '?')) {
                    fetch(`/api/requests/${referenceNumber}/confirm`, {method: 'POST'})
                        .then(response => response.json())
                        .then(data => {
                            alert('Request confirmed successfully!');
                            location.reload();
                        })
                        .catch(error => alert('Failed to confirm request: ' + error));
                }
            }
        </script>
    </head>
    <body>
        <div class="header">
            <div class="container">
                <h1>🏢 Provider Portal</h1>
                <p>Manage your emergency response services</p>
            </div>
        </div>
        
        <div class="container">
            <!-- Provider Statistics -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{{ stats.total_resources }}</div>
                    <div class="stat-label">Your Resources</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.total_requests }}</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.pending_requests }}</div>
                    <div class="stat-label">Pending Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">₦{{ "%.2f"|format(stats.total_earnings) }}</div>
                    <div class="stat-label">Total Earnings</div>
                </div>
            </div>
            
            <!-- Tabbed Content -->
            <div class="nav-tabs">
                <div class="nav-tab active" onclick="showTab('pending-requests')">Pending Requests</div>
                <div class="nav-tab" onclick="showTab('my-resources')">My Resources</div>
                <div class="nav-tab" onclick="showTab('earnings')">Earnings</div>
            </div>
            
            <!-- Pending Requests Tab -->
            <div id="pending-requests" class="tab-content section">
                <h2>📋 Requests Awaiting Your Service</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Reference</th>
                            <th>Service Type</th>
                            <th>Location</th>
                            <th>Resource</th>
                            <th>Cost</th>
                            <th>Created</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for request in pending_requests %}
                        <tr>
                            <td><strong>{{ request.reference_number }}</strong></td>
                            <td>{{ request.resource_type.value.title() }}</td>
                            <td>{{ request.location }}</td>
                            <td>{{ request.resource.name if request.resource else 'N/A' }}</td>
                            <td>
                                {% if request.total_cost > 0 %}
                                    ₦{{ request.total_cost }}
                                {% else %}
                                    Free
                                {% endif %}
                            </td>
                            <td>{{ request.created_at.strftime('%H:%M %d/%m') }}</td>
                            <td>
                                <button class="btn btn-success" onclick="confirmRequest('{{ request.reference_number }}')">
                                    Confirm Service
                                </button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% if not pending_requests %}
                <p>No pending requests at the moment.</p>
                {% endif %}
            </div>
            
            <!-- My Resources Tab -->
            <div id="my-resources" class="tab-content section" style="display: none;">
                <h2>🏢 Your Resources</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Location</th>
                            <th>Capacity</th>
                            <th>Available</th>
                            <th>Price</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for resource in my_resources %}
                        <tr>
                            <td><strong>{{ resource.name }}</strong></td>
                            <td>{{ resource.resource_type.value.title() }}</td>
                            <td>{{ resource.location }}</td>
                            <td>{{ resource.total_capacity }}</td>
                            <td>{{ resource.available_capacity }}</td>
                            <td>
                                {% if resource.price_per_unit > 0 %}
                                    ₦{{ resource.price_per_unit }}
                                {% else %}
                                    Free
                                {% endif %}
                            </td>
                            <td>{{ 'Active' if resource.is_active else 'Inactive' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                <button class="btn">+ Add New Resource</button>
            </div>
            
            <!-- Earnings Tab -->
            <div id="earnings" class="tab-content section" style="display: none;">
                <h2>💰 Your Earnings</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">₦{{ "%.2f"|format(earnings.this_month) }}</div>
                        <div class="stat-label">This Month</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">₦{{ "%.2f"|format(earnings.last_month) }}</div>
                        <div class="stat-label">Last Month</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ earnings.completed_services }}</div>
                        <div class="stat-label">Services Completed</div>
                    </div>
                </div>
                
                <h3>Recent Payments</h3>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Reference</th>
                            <th>Service</th>
                            <th>Amount</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for payment in recent_payments %}
                        <tr>
                            <td>{{ payment.created_at.strftime('%d/%m/%Y') }}</td>
                            <td>{{ payment.emergency_request.reference_number }}</td>
                            <td>{{ payment.emergency_request.resource_type.value.title() }}</td>
                            <td>₦{{ payment.amount }}</td>
                            <td class="status-{{ payment.status.value }}">{{ payment.status.value.title() }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        # This would normally get the current provider from session/auth
        # For demo purposes, we'll use the first provider
        provider = Provider.query.first()
        
        if not provider:
            return jsonify({'error': 'Provider not found'}), 404
        
        # Get provider statistics
        my_resources = Resource.query.filter_by(provider_id=provider.id).all()
        total_requests = EmergencyRequest.query.join(Resource).filter(
            Resource.provider_id == provider.id
        ).count()
        
        pending_requests = EmergencyRequest.query.join(Resource).filter(
            Resource.provider_id == provider.id,
            EmergencyRequest.status == RequestStatus.MATCHED
        ).all()
        
        # Calculate earnings
        total_earnings = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.provider_id == provider.id,
            Payment.status == PaymentStatus.COMPLETED
        ).scalar() or 0
        
        # Monthly earnings
        this_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        this_month_earnings = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.provider_id == provider.id,
            Payment.status == PaymentStatus.COMPLETED,
            Payment.created_at >= this_month_start
        ).scalar() or 0
        
        last_month_earnings = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.provider_id == provider.id,
            Payment.status == PaymentStatus.COMPLETED,
            Payment.created_at >= last_month_start,
            Payment.created_at < this_month_start
        ).scalar() or 0
        
        completed_services = EmergencyRequest.query.join(Resource).filter(
            Resource.provider_id == provider.id,
            EmergencyRequest.status == RequestStatus.COMPLETED
        ).count()
        
        # Recent payments
        recent_payments = Payment.query.filter_by(provider_id=provider.id).order_by(
            Payment.created_at.desc()
        ).limit(10).all()
        
        stats = {
            'total_resources': len(my_resources),
            'total_requests': total_requests,
            'pending_requests': len(pending_requests),
            'total_earnings': total_earnings
        }
        
        earnings = {
            'this_month': this_month_earnings,
            'last_month': last_month_earnings,
            'completed_services': completed_services
        }
        
        return render_template_string(
            provider_html,
            provider=provider,
            stats=stats,
            pending_requests=pending_requests,
            my_resources=my_resources,
            earnings=earnings,
            recent_payments=recent_payments
        )
        
    except Exception as e:
        current_app.logger.error(f"Error loading provider dashboard: {e}")
        return jsonify({'error': 'Failed to load provider dashboard'}), 500

@bp.route('/register', methods=['GET', 'POST'])
@audit_log('provider_registration')
def register():
    """Provider registration"""
    if request.method == 'GET':
        registration_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Provider Registration - Emergency Response System</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
                .container { max-width: 600px; margin: 50px auto; padding: 20px; }
                .form-card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .form-group { margin: 20px 0; }
                .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
                .form-group input, .form-group select, .form-group textarea { 
                    width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; 
                }
                .btn { background: #2196f3; color: white; padding: 12px 30px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
                .btn:hover { background: #1976d2; }
                .header { text-align: center; margin-bottom: 30px; }
                .header h1 { color: #2196f3; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="form-card">
                    <div class="header">
                        <h1>🏢 Provider Registration</h1>
                        <p>Join our network of emergency service providers</p>
                    </div>
                    
                    <form method="POST">
                        <div class="form-group">
                            <label for="organization_name">Organization Name *</label>
                            <input type="text" id="organization_name" name="organization_name" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="contact_person">Contact Person *</label>
                            <input type="text" id="contact_person" name="contact_person" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="email">Email Address *</label>
                            <input type="email" id="email" name="email" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="phone">Phone Number *</label>
                            <input type="tel" id="phone" name="phone" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="organization_type">Organization Type *</label>
                            <select id="organization_type" name="organization_type" required>
                                <option value="">Select type...</option>
                                <option value="ngo">NGO/Non-Profit</option>
                                <option value="government">Government Agency</option>
                                <option value="private">Private Company</option>
                                <option value="volunteer">Volunteer Group</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="services">Services You Can Provide</label>
                            <textarea id="services" name="services" rows="3" placeholder="Describe the emergency services you can provide..."></textarea>
                        </div>
                        
                        <div class="form-group">
                            <label for="coverage_area">Coverage Area</label>
                            <input type="text" id="coverage_area" name="coverage_area" placeholder="e.g., Lokoja, Kogi State">
                        </div>
                        
                        <div class="form-group">
                            <input type="checkbox" id="terms" name="terms" required>
                            <label for="terms">I agree to the terms and conditions and privacy policy</label>
                        </div>
                        
                        <button type="submit" class="btn">Register as Provider</button>
                    </form>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(registration_html)
    
    else:  # POST
        try:
            data = request.form.to_dict()
            
            # Validate required fields
            required_fields = ['organization_name', 'contact_person', 'email', 'phone', 'organization_type']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Create user first (simplified - in real app, this would be more complex)
            from app.models import User, UserRole, encrypt_data
            
            user = User(data['phone'], data['contact_person'], UserRole.NGO)
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Create provider
            provider = Provider(
                user_id=user.id,
                organization_name=data['organization_name'],
                encrypted_contact_person=encrypt_data(data['contact_person']),
                encrypted_email=encrypt_data(data['email']),
                verification_status='pending'
            )
            
            db.session.add(provider)
            db.session.commit()
            
            return jsonify({
                'message': 'Registration successful! Your application is under review.',
                'provider_id': provider.id
            }), 201
            
        except Exception as e:
            current_app.logger.error(f"Error in provider registration: {e}")
            db.session.rollback()
            return jsonify({'error': 'Registration failed'}), 500