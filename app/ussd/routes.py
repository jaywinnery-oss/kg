"""
USSD Routes for Emergency Response System
Handles Africa's Talking USSD callbacks with comprehensive security
"""
from flask import request, jsonify, current_app, g
from app.ussd import bp
from app import db
from app.models import User, USSDSession, EmergencyRequest, Resource, ResourceType, RequestStatus
from app.security import (
    SecurityService, audit_log, rate_limit_by_phone, 
    validate_request_signature, FraudDetection
)
from app.services.sms_service import SMSService
from app.services.matching_service import MatchingService
import json
from datetime import datetime

class USSDMenuHandler:
    """Handles USSD menu navigation and state management"""
    
    def __init__(self, session_id, phone_number, text):
        self.session_id = session_id
        self.phone_number = SecurityService.normalize_phone_number(phone_number)
        self.text = text
        self.user = None
        self.session = None
        
    def process_request(self):
        """Main request processing logic"""
        try:
            # Get or create user
            self.user = self._get_or_create_user()
            
            # Check rate limiting
            if self.user.is_rate_limited('ussd', 3):
                return self._end_session("Too many requests. Please try again later.")
            
            # Get or create session
            self.session = self._get_or_create_session()
            
            # Check for suspicious activity
            if SecurityService.detect_suspicious_activity(
                self.user.id, 'ussd_request', {'location': self.text}
            ):
                SecurityService.log_security_event(
                    'SUSPICIOUS_USSD_ACTIVITY',
                    f'Suspicious activity from {self.phone_number}',
                    'WARNING'
                )
                return self._end_session("Request blocked for security reasons.")
            
            # Process based on current step
            if self.text == "":
                return self._show_main_menu()
            else:
                return self._handle_user_input()
                
        except Exception as e:
            current_app.logger.error(f"USSD processing error: {e}")
            return self._end_session("Service temporarily unavailable. Please try again.")
    
    def _get_or_create_user(self):
        """Get existing user or create new one"""
        from app.models import hash_phone_number
        phone_hash = hash_phone_number(self.phone_number)
        
        user = User.query.filter_by(phone_hash=phone_hash).first()
        if not user:
            user = User(self.phone_number)
            db.session.add(user)
            db.session.commit()
            
        return user
    
    def _get_or_create_session(self):
        """Get existing session or create new one"""
        session = USSDSession.query.filter_by(session_id=self.session_id).first()
        
        if not session or session.is_expired():
            # Create new session
            if session:
                db.session.delete(session)
            
            session = USSDSession(self.session_id, self.user.id)
            db.session.add(session)
            db.session.commit()
        else:
            # Extend existing session
            session.extend_session()
            db.session.commit()
        
        return session
    
    def _show_main_menu(self):
        """Display main USSD menu"""
        self.session.current_step = 'main_menu'
        db.session.commit()
        
        menu = (
            "🚨 Emergency Response System\\n"
            "Select service needed:\\n"
            "1. 🏠 Shelter\\n"
            "2. 🍽️ Food\\n"
            "3. 🚗 Transport\\n"
            "0. Exit"
        )
        
        return self._continue_session(menu)
    
    def _handle_user_input(self):
        """Handle user input based on current step"""
        inputs = self.text.split('*')
        current_input = inputs[-1] if inputs else ""
        
        session_data = self.session.get_session_data()
        
        if self.session.current_step == 'main_menu':
            return self._handle_main_menu_selection(current_input)
        elif self.session.current_step == 'location_input':
            return self._handle_location_input(current_input, session_data)
        elif self.session.current_step == 'resource_selection':
            return self._handle_resource_selection(current_input, session_data)
        elif self.session.current_step == 'confirmation':
            return self._handle_confirmation(current_input, session_data)
        else:
            return self._show_main_menu()
    
    def _handle_main_menu_selection(self, selection):
        """Handle main menu selection"""
        resource_types = {
            '1': ResourceType.SHELTER,
            '2': ResourceType.FOOD,
            '3': ResourceType.TRANSPORT
        }
        
        if selection == '0':
            return self._end_session("Thank you for using Emergency Response System.")
        
        if selection not in resource_types:
            return self._continue_session(
                "Invalid selection. Please choose:\\n"
                "1. Shelter\\n2. Food\\n3. Transport\\n0. Exit"
            )
        
        # Store selection and move to location input
        session_data = {'resource_type': resource_types[selection].value}
        self.session.set_session_data(session_data)
        self.session.current_step = 'location_input'
        db.session.commit()
        
        return self._continue_session(
            f"You selected: {resource_types[selection].value.title()}\\n"
            "Please enter your location (e.g., Lokoja, Ganaja):"
        )
    
    def _handle_location_input(self, location, session_data):
        """Handle location input and show available resources"""
        if not location or len(location.strip()) < 2:
            return self._continue_session("Please enter a valid location:")
        
        # Store location
        session_data['location'] = location.strip()
        self.session.set_session_data(session_data)
        
        # Find available resources
        resource_type = ResourceType(session_data['resource_type'])
        resources = MatchingService.find_nearby_resources(
            resource_type, location, radius_km=50
        )
        
        if not resources:
            return self._end_session(
                f"Sorry, no {resource_type.value} available near {location}. "
                "Please try again later or contact emergency services."
            )
        
        # Show available resources
        menu = f"Available {resource_type.value} near {location}:\\n"
        for i, resource in enumerate(resources[:5], 1):  # Limit to 5 options
            status = "✅ Available" if resource.available_capacity > 0 else "❌ Full"
            price = f" (₦{resource.price_per_unit})" if resource.price_per_unit > 0 else " (Free)"
            menu += f"{i}. {resource.name} - {status}{price}\\n"
        
        menu += "0. Back to main menu"
        
        # Store resources for selection
        session_data['resources'] = [r.id for r in resources[:5]]
        self.session.set_session_data(session_data)
        self.session.current_step = 'resource_selection'
        db.session.commit()
        
        return self._continue_session(menu)
    
    def _handle_resource_selection(self, selection, session_data):
        """Handle resource selection"""
        if selection == '0':
            return self._show_main_menu()
        
        try:
            selection_idx = int(selection) - 1
            if selection_idx < 0 or selection_idx >= len(session_data.get('resources', [])):
                raise ValueError("Invalid selection")
            
            resource_id = session_data['resources'][selection_idx]
            resource = Resource.query.get(resource_id)
            
            if not resource or resource.available_capacity <= 0:
                return self._continue_session(
                    "Selected resource is no longer available. Please choose another:\\n"
                    "Or press 0 to go back to main menu."
                )
            
            # Store selected resource
            session_data['selected_resource_id'] = resource_id
            self.session.set_session_data(session_data)
            self.session.current_step = 'confirmation'
            db.session.commit()
            
            # Show confirmation
            cost_info = f"Cost: ₦{resource.price_per_unit}" if resource.price_per_unit > 0 else "Cost: Free"
            confirmation_msg = (
                f"Confirm your request:\\n"
                f"Service: {session_data['resource_type'].title()}\\n"
                f"Provider: {resource.name}\\n"
                f"Location: {resource.location}\\n"
                f"{cost_info}\\n\\n"
                f"1. Confirm\\n"
                f"2. Cancel"
            )
            
            return self._continue_session(confirmation_msg)
            
        except (ValueError, IndexError):
            return self._continue_session("Invalid selection. Please choose a number from the list:")
    
    def _handle_confirmation(self, selection, session_data):
        """Handle request confirmation"""
        if selection == '2':
            return self._end_session("Request cancelled. Stay safe!")
        
        if selection != '1':
            return self._continue_session("Please choose:\\n1. Confirm\\n2. Cancel")
        
        # Create emergency request
        try:
            resource_id = session_data['selected_resource_id']
            resource = Resource.query.get(resource_id)
            
            if not resource or resource.available_capacity <= 0:
                return self._end_session("Resource no longer available. Please try again.")
            
            # Check for duplicate requests
            if FraudDetection.check_duplicate_requests(
                self.user.id, 
                ResourceType(session_data['resource_type']), 
                session_data['location']
            ):
                return self._end_session(
                    "You have a similar pending request. "
                    "Please wait for it to be processed."
                )
            
            # Create the request
            emergency_request = EmergencyRequest(
                user_id=self.user.id,
                resource_type=ResourceType(session_data['resource_type']),
                location=session_data['location'],
                resource_id=resource_id,
                total_cost=resource.price_per_unit
            )
            
            db.session.add(emergency_request)
            
            # Update resource capacity
            resource.update_capacity(1)
            
            # Set request as matched
            emergency_request.status = RequestStatus.MATCHED
            emergency_request.matched_at = datetime.utcnow()
            
            db.session.commit()
            
            # Send SMS confirmation
            try:
                SMSService.send_confirmation_sms(
                    self.phone_number,
                    emergency_request.reference_number,
                    resource
                )
            except Exception as e:
                current_app.logger.error(f"Failed to send SMS: {e}")
            
            # Notify provider
            try:
                SMSService.send_provider_notification(
                    resource.contact_phone,
                    emergency_request,
                    self.user
                )
            except Exception as e:
                current_app.logger.error(f"Failed to notify provider: {e}")
            
            return self._end_session(
                f"✅ Request confirmed!\\n"
                f"Reference: {emergency_request.reference_number}\\n"
                f"Provider: {resource.name}\\n"
                f"Contact: {resource.contact_phone}\\n"
                f"You will receive SMS confirmation shortly."
            )
            
        except Exception as e:
            current_app.logger.error(f"Failed to create emergency request: {e}")
            db.session.rollback()
            return self._end_session("Failed to process request. Please try again.")
    
    def _continue_session(self, message):
        """Continue USSD session with message"""
        return f"CON {message}"
    
    def _end_session(self, message):
        """End USSD session with message"""
        # Clean up session
        if self.session:
            db.session.delete(self.session)
            db.session.commit()
        
        return f"END {message}"

@bp.route('/callback', methods=['POST'])
@rate_limit_by_phone("3 per hour")
@audit_log('ussd_request')
def ussd_callback():
    """
    Main USSD callback endpoint for Africa's Talking
    This is where you'll configure your callback URL in Africa's Talking dashboard
    """
    try:
        # Get request data
        data = request.form.to_dict() if request.form else request.get_json()
        
        if not data:
            current_app.logger.error("No data received in USSD callback")
            return "END Service temporarily unavailable", 400
        
        # Validate request
        is_valid, error_msg = SecurityService.validate_ussd_request(data)
        if not is_valid:
            current_app.logger.warning(f"Invalid USSD request: {error_msg}")
            return f"END {error_msg}", 400
        
        # Extract parameters
        session_id = data.get('sessionId')
        phone_number = data.get('phoneNumber')
        text = data.get('text', '')
        
        current_app.logger.info(f"USSD request: {phone_number} - {text}")
        
        # Process request
        handler = USSDMenuHandler(session_id, phone_number, text)
        response = handler.process_request()
        
        current_app.logger.info(f"USSD response: {response}")
        return response
        
    except Exception as e:
        current_app.logger.error(f"USSD callback error: {e}")
        return "END Service temporarily unavailable. Please try again.", 500

@bp.route('/test', methods=['POST'])
@audit_log('ussd_test')
def test_ussd():
    """
    Test endpoint for USSD functionality
    Use this for testing without Africa's Talking
    """
    if not current_app.config.get('DEBUG'):
        return jsonify({'error': 'Test endpoint only available in debug mode'}), 403
    
    try:
        data = request.get_json()
        
        # Provide default test data
        test_data = {
            'sessionId': data.get('sessionId', 'test_session_123'),
            'phoneNumber': data.get('phoneNumber', '+2348012345678'),
            'text': data.get('text', '')
        }
        
        # Validate request
        is_valid, error_msg = SecurityService.validate_ussd_request(test_data)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # Process request
        handler = USSDMenuHandler(
            test_data['sessionId'],
            test_data['phoneNumber'],
            test_data['text']
        )
        response = handler.process_request()
        
        return jsonify({
            'response': response,
            'session_id': test_data['sessionId'],
            'phone_number': test_data['phoneNumber'],
            'input_text': test_data['text']
        })
        
    except Exception as e:
        current_app.logger.error(f"USSD test error: {e}")
        return jsonify({'error': 'Test failed'}), 500

@bp.route('/sessions/cleanup', methods=['POST'])
@audit_log('session_cleanup')
def cleanup_sessions():
    """Clean up expired USSD sessions"""
    try:
        from app.security import cleanup_expired_sessions
        cleaned_count = cleanup_expired_sessions()
        
        return jsonify({
            'message': f'Cleaned up {cleaned_count} expired sessions',
            'count': cleaned_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Session cleanup error: {e}")
        return jsonify({'error': 'Cleanup failed'}), 500