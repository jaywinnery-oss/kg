"""
API Routes for Emergency Response System
RESTful endpoints for resource management and system monitoring
"""
from flask import request, jsonify, current_app, g
from app.api import bp
from app import db, limiter
from app.models import (
    Resource, ResourceType, EmergencyRequest, RequestStatus, 
    User, Provider, AuditLog, Payment, PaymentStatus
)
from app.security import (
    audit_log, require_role, SecurityService, FraudDetection
)
from app.services.matching_service import MatchingService
from app.services.sms_service import SMSService
from datetime import datetime, timedelta
import json

@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@bp.route('/resources', methods=['GET'])
@limiter.limit("100 per hour")
@audit_log('api_resources_list')
def list_resources():
    """List all active resources with optional filtering"""
    try:
        # Get query parameters
        resource_type = request.args.get('type')
        location = request.args.get('location')
        available_only = request.args.get('available_only', 'false').lower() == 'true'
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)  # Max 100 per page
        
        # Build query
        query = Resource.query.filter(Resource.is_active == True)
        
        if resource_type:
            try:
                resource_type_enum = ResourceType(resource_type.lower())
                query = query.filter(Resource.resource_type == resource_type_enum)
            except ValueError:
                return jsonify({'error': 'Invalid resource type'}), 400
        
        if location:
            query = query.filter(Resource.location.ilike(f'%{location}%'))
        
        if available_only:
            query = query.filter(Resource.available_capacity > 0)
        
        # Paginate results
        resources = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format response
        resource_list = []
        for resource in resources.items:
            resource_data = {
                'id': resource.id,
                'name': resource.name,
                'description': resource.description,
                'type': resource.resource_type.value,
                'location': resource.location,
                'total_capacity': resource.total_capacity,
                'available_capacity': resource.available_capacity,
                'price_per_unit': resource.price_per_unit,
                'currency': resource.currency,
                'organization': resource.provider.organization_name if resource.provider else None,
                'created_at': resource.created_at.isoformat()
            }
            
            # Include coordinates if available
            if resource.latitude and resource.longitude:
                resource_data['coordinates'] = {
                    'latitude': resource.latitude,
                    'longitude': resource.longitude
                }
            
            resource_list.append(resource_data)
        
        return jsonify({
            'resources': resource_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': resources.total,
                'pages': resources.pages,
                'has_next': resources.has_next,
                'has_prev': resources.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing resources: {e}")
        return jsonify({'error': 'Failed to retrieve resources'}), 500

@bp.route('/resources', methods=['POST'])
@limiter.limit("10 per hour")
@require_role(['admin', 'ngo', 'government'])
@audit_log('api_resource_create')
def create_resource():
    """Create a new resource"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['name', 'type', 'location', 'total_capacity', 'provider_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate resource type
        try:
            resource_type = ResourceType(data['type'].lower())
        except ValueError:
            return jsonify({'error': 'Invalid resource type'}), 400
        
        # Validate provider
        provider = Provider.query.get(data['provider_id'])
        if not provider:
            return jsonify({'error': 'Provider not found'}), 404
        
        # Create resource
        resource = Resource(
            provider_id=data['provider_id'],
            name=data['name'],
            description=data.get('description'),
            resource_type=resource_type,
            location=data['location'],
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            total_capacity=int(data['total_capacity']),
            available_capacity=int(data.get('available_capacity', data['total_capacity'])),
            price_per_unit=float(data.get('price_per_unit', 0)),
            currency=data.get('currency', 'NGN')
        )
        
        # Encrypt contact phone if provided
        if data.get('contact_phone'):
            from app.models import encrypt_data
            resource.encrypted_contact_phone = encrypt_data(data['contact_phone'])
        
        db.session.add(resource)
        db.session.commit()
        
        return jsonify({
            'message': 'Resource created successfully',
            'resource_id': resource.id
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating resource: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create resource'}), 500

@bp.route('/resources/<int:resource_id>', methods=['PUT'])
@limiter.limit("20 per hour")
@require_role(['admin', 'ngo', 'government'])
@audit_log('api_resource_update')
def update_resource(resource_id):
    """Update an existing resource"""
    try:
        resource = Resource.query.get_or_404(resource_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update allowed fields
        updatable_fields = [
            'name', 'description', 'location', 'total_capacity', 
            'available_capacity', 'price_per_unit', 'is_active'
        ]
        
        for field in updatable_fields:
            if field in data:
                if field == 'available_capacity':
                    # Validate capacity constraints
                    new_capacity = int(data[field])
                    if new_capacity > resource.total_capacity:
                        return jsonify({
                            'error': 'Available capacity cannot exceed total capacity'
                        }), 400
                    resource.available_capacity = new_capacity
                elif field == 'total_capacity':
                    resource.total_capacity = int(data[field])
                elif field == 'price_per_unit':
                    resource.price_per_unit = float(data[field])
                elif field == 'is_active':
                    resource.is_active = bool(data[field])
                else:
                    setattr(resource, field, data[field])
        
        # Update contact phone if provided
        if 'contact_phone' in data:
            from app.models import encrypt_data
            resource.encrypted_contact_phone = encrypt_data(data['contact_phone'])
        
        resource.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Resource updated successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Error updating resource: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update resource'}), 500

@bp.route('/requests', methods=['GET'])
@limiter.limit("100 per hour")
@require_role(['admin', 'ngo', 'government'])
@audit_log('api_requests_list')
def list_requests():
    """List emergency requests with filtering"""
    try:
        # Get query parameters
        status = request.args.get('status')
        resource_type = request.args.get('type')
        location = request.args.get('location')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # Build query
        query = EmergencyRequest.query
        
        if status:
            try:
                status_enum = RequestStatus(status.lower())
                query = query.filter(EmergencyRequest.status == status_enum)
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        if resource_type:
            try:
                resource_type_enum = ResourceType(resource_type.lower())
                query = query.filter(EmergencyRequest.resource_type == resource_type_enum)
            except ValueError:
                return jsonify({'error': 'Invalid resource type'}), 400
        
        if location:
            query = query.filter(EmergencyRequest.location.ilike(f'%{location}%'))
        
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from)
                query = query.filter(EmergencyRequest.created_at >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format'}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to)
                query = query.filter(EmergencyRequest.created_at <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format'}), 400
        
        # Order by creation date (newest first)
        query = query.order_by(EmergencyRequest.created_at.desc())
        
        # Paginate results
        requests = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format response
        request_list = []
        for req in requests.items:
            request_data = {
                'id': req.id,
                'reference_number': req.reference_number,
                'resource_type': req.resource_type.value,
                'location': req.location,
                'status': req.status.value,
                'priority_level': req.priority_level,
                'total_cost': req.total_cost,
                'payment_status': req.payment_status.value,
                'created_at': req.created_at.isoformat(),
                'matched_at': req.matched_at.isoformat() if req.matched_at else None,
                'confirmed_at': req.confirmed_at.isoformat() if req.confirmed_at else None,
                'completed_at': req.completed_at.isoformat() if req.completed_at else None
            }
            
            # Include resource info if matched
            if req.resource:
                request_data['resource'] = {
                    'id': req.resource.id,
                    'name': req.resource.name,
                    'location': req.resource.location,
                    'organization': req.resource.provider.organization_name if req.resource.provider else None
                }
            
            request_list.append(request_data)
        
        return jsonify({
            'requests': request_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': requests.total,
                'pages': requests.pages,
                'has_next': requests.has_next,
                'has_prev': requests.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing requests: {e}")
        return jsonify({'error': 'Failed to retrieve requests'}), 500

@bp.route('/requests/<reference_number>/confirm', methods=['POST'])
@limiter.limit("50 per hour")
@require_role(['admin', 'ngo', 'government', 'volunteer'])
@audit_log('api_request_confirm')
def confirm_request(reference_number):
    """Confirm service delivery for a request"""
    try:
        emergency_request = EmergencyRequest.query.filter_by(
            reference_number=reference_number
        ).first_or_404()
        
        if emergency_request.status != RequestStatus.MATCHED:
            return jsonify({
                'error': 'Request must be in matched status to confirm'
            }), 400
        
        # Update request status
        emergency_request.status = RequestStatus.CONFIRMED
        emergency_request.confirmed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send confirmation SMS to user
        try:
            SMSService.send_completion_notification(
                emergency_request.user.phone_number,
                reference_number,
                emergency_request.resource.name
            )
        except Exception as e:
            current_app.logger.error(f"Failed to send completion SMS: {e}")
        
        return jsonify({
            'message': 'Request confirmed successfully',
            'reference_number': reference_number,
            'status': 'confirmed'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error confirming request: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to confirm request'}), 500

@bp.route('/stats', methods=['GET'])
@limiter.limit("60 per hour")
@audit_log('api_stats')
def get_stats():
    """Get system statistics"""
    try:
        # Get date range for stats
        days = int(request.args.get('days', 7))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Request statistics
        total_requests = EmergencyRequest.query.count()
        recent_requests = EmergencyRequest.query.filter(
            EmergencyRequest.created_at >= start_date
        ).count()
        
        # Status breakdown
        status_stats = {}
        for status in RequestStatus:
            count = EmergencyRequest.query.filter(
                EmergencyRequest.status == status
            ).count()
            status_stats[status.value] = count
        
        # Resource type breakdown
        type_stats = {}
        for resource_type in ResourceType:
            count = EmergencyRequest.query.filter(
                EmergencyRequest.resource_type == resource_type
            ).count()
            type_stats[resource_type.value] = count
        
        # Resource utilization
        utilization_stats = MatchingService.get_resource_utilization_stats()
        
        # Response time statistics
        completed_requests = EmergencyRequest.query.filter(
            EmergencyRequest.status == RequestStatus.COMPLETED,
            EmergencyRequest.created_at >= start_date
        ).all()
        
        response_times = []
        for req in completed_requests:
            if req.matched_at:
                response_time = (req.matched_at - req.created_at).total_seconds() / 60  # minutes
                response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return jsonify({
            'period_days': days,
            'total_requests': total_requests,
            'recent_requests': recent_requests,
            'status_breakdown': status_stats,
            'type_breakdown': type_stats,
            'resource_utilization': utilization_stats,
            'average_response_time_minutes': round(avg_response_time, 2),
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating stats: {e}")
        return jsonify({'error': 'Failed to generate statistics'}), 500

@bp.route('/matching/auto-match', methods=['POST'])
@limiter.limit("10 per hour")
@require_role(['admin'])
@audit_log('api_auto_match')
def trigger_auto_match():
    """Trigger automatic matching of pending requests"""
    try:
        result = MatchingService.auto_match_pending_requests()
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in auto-matching: {e}")
        return jsonify({'error': 'Auto-matching failed'}), 500

@bp.route('/security/audit-logs', methods=['GET'])
@limiter.limit("30 per hour")
@require_role(['admin'])
@audit_log('api_audit_logs')
def get_audit_logs():
    """Get audit logs for security monitoring"""
    try:
        # Get query parameters
        action = request.args.get('action')
        user_id = request.args.get('user_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        # Build query
        query = AuditLog.query
        
        if action:
            query = query.filter(AuditLog.action.ilike(f'%{action}%'))
        
        if user_id:
            query = query.filter(AuditLog.user_id == int(user_id))
        
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from)
                query = query.filter(AuditLog.timestamp >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format'}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to)
                query = query.filter(AuditLog.timestamp <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format'}), 400
        
        # Order by timestamp (newest first)
        query = query.order_by(AuditLog.timestamp.desc())
        
        # Paginate results
        logs = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format response
        log_list = []
        for log in logs.items:
            log_data = {
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'ip_address': log.ip_address,
                'session_id': log.session_id
            }
            
            # Include details if available
            if log.details:
                try:
                    log_data['details'] = json.loads(log.details)
                except:
                    log_data['details'] = log.details
            
            log_list.append(log_data)
        
        return jsonify({
            'logs': log_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': logs.total,
                'pages': logs.pages,
                'has_next': logs.has_next,
                'has_prev': logs.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving audit logs: {e}")
        return jsonify({'error': 'Failed to retrieve audit logs'}), 500