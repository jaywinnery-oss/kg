"""
SMS Service for Emergency Response System
Integrates with Africa's Talking SMS API for notifications
"""
import requests
import json
from flask import current_app
from app.security import SecurityService
from datetime import datetime

class SMSService:
    """SMS service using Africa's Talking API"""
    
    @staticmethod
    def _get_api_config():
        """Get Africa's Talking API configuration"""
        return {
            'username': current_app.config.get('AFRICAS_TALKING_USERNAME'),
            'api_key': current_app.config.get('AFRICAS_TALKING_API_KEY'),
            'sender_id': current_app.config.get('SMS_SENDER_ID', 'EMERGENCY')
        }
    
    @staticmethod
    def _send_sms(to, message, sender_id=None):
        """
        Send SMS using Africa's Talking API
        
        Args:
            to (str): Phone number in international format
            message (str): SMS message content
            sender_id (str): Sender ID (optional)
        
        Returns:
            dict: API response
        """
        config = SMSService._get_api_config()
        
        if not config['api_key']:
            current_app.logger.warning("SMS API key not configured")
            return {'status': 'error', 'message': 'SMS service not configured'}
        
        # Validate phone number
        if not SecurityService.validate_phone_number(to):
            return {'status': 'error', 'message': 'Invalid phone number'}
        
        # Normalize phone number
        to = SecurityService.normalize_phone_number(to)
        
        # Prepare API request
        url = "https://api.sandbox.africastalking.com/version1/messaging"  # Use production URL in production
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'apiKey': config['api_key']
        }
        
        data = {
            'username': config['username'],
            'to': to,
            'message': message,
            'from': sender_id or config['sender_id']
        }
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            current_app.logger.info(f"SMS sent to {to[:8]}****: {result}")
            
            return {
                'status': 'success',
                'response': result,
                'message_id': result.get('SMSMessageData', {}).get('Recipients', [{}])[0].get('messageId')
            }
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"SMS API error: {e}")
            return {'status': 'error', 'message': f'SMS API error: {str(e)}'}
        except Exception as e:
            current_app.logger.error(f"SMS sending error: {e}")
            return {'status': 'error', 'message': f'SMS error: {str(e)}'}
    
    @staticmethod
    def send_confirmation_sms(phone_number, reference_number, resource):
        """
        Send confirmation SMS to user after successful request
        
        Args:
            phone_number (str): User's phone number
            reference_number (str): Emergency request reference number
            resource (Resource): Matched resource
        """
        try:
            cost_info = f"Cost: ₦{resource.price_per_unit}" if resource.price_per_unit > 0 else "FREE"
            
            message = (
                f"🚨 EMERGENCY REQUEST CONFIRMED\n"
                f"Ref: {reference_number}\n"
                f"Service: {resource.resource_type.value.title()}\n"
                f"Provider: {resource.name}\n"
                f"Location: {resource.location}\n"
                f"Contact: {resource.contact_phone}\n"
                f"{cost_info}\n"
                f"Show this reference to the provider."
            )
            
            result = SMSService._send_sms(phone_number, message)
            
            if result['status'] == 'success':
                current_app.logger.info(f"Confirmation SMS sent for {reference_number}")
            else:
                current_app.logger.error(f"Failed to send confirmation SMS: {result['message']}")
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error sending confirmation SMS: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def send_provider_notification(phone_number, emergency_request, user):
        """
        Send notification SMS to service provider
        
        Args:
            phone_number (str): Provider's phone number
            emergency_request (EmergencyRequest): The emergency request
            user (User): The user who made the request
        """
        try:
            # Anonymize user phone for privacy
            masked_phone = f"{user.phone_number[:4]}****{user.phone_number[-4:]}"
            
            message = (
                f"🚨 NEW EMERGENCY REQUEST\n"
                f"Ref: {emergency_request.reference_number}\n"
                f"Service: {emergency_request.resource_type.value.title()}\n"
                f"Location: {emergency_request.location}\n"
                f"Contact: {masked_phone}\n"
                f"Time: {emergency_request.created_at.strftime('%H:%M %d/%m/%Y')}\n"
                f"Please confirm service delivery with reference number."
            )
            
            result = SMSService._send_sms(phone_number, message)
            
            if result['status'] == 'success':
                current_app.logger.info(f"Provider notification sent for {emergency_request.reference_number}")
            else:
                current_app.logger.error(f"Failed to send provider notification: {result['message']}")
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error sending provider notification: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def send_completion_notification(phone_number, reference_number, provider_name):
        """
        Send completion notification to user
        
        Args:
            phone_number (str): User's phone number
            reference_number (str): Emergency request reference number
            provider_name (str): Name of the service provider
        """
        try:
            message = (
                f"✅ SERVICE COMPLETED\n"
                f"Ref: {reference_number}\n"
                f"Provider: {provider_name}\n"
                f"Thank you for using Emergency Response System.\n"
                f"Stay safe!"
            )
            
            result = SMSService._send_sms(phone_number, message)
            
            if result['status'] == 'success':
                current_app.logger.info(f"Completion notification sent for {reference_number}")
            else:
                current_app.logger.error(f"Failed to send completion notification: {result['message']}")
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error sending completion notification: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def send_payment_notification(phone_number, reference_number, amount, status):
        """
        Send payment notification SMS
        
        Args:
            phone_number (str): User's phone number
            reference_number (str): Emergency request reference number
            amount (float): Payment amount
            status (str): Payment status
        """
        try:
            if status == 'completed':
                message = (
                    f"💳 PAYMENT SUCCESSFUL\n"
                    f"Ref: {reference_number}\n"
                    f"Amount: ₦{amount:.2f}\n"
                    f"Thank you for your payment."
                )
            elif status == 'failed':
                message = (
                    f"❌ PAYMENT FAILED\n"
                    f"Ref: {reference_number}\n"
                    f"Amount: ₦{amount:.2f}\n"
                    f"Please try again or contact support."
                )
            else:
                message = (
                    f"⏳ PAYMENT PENDING\n"
                    f"Ref: {reference_number}\n"
                    f"Amount: ₦{amount:.2f}\n"
                    f"Processing your payment..."
                )
            
            result = SMSService._send_sms(phone_number, message)
            
            if result['status'] == 'success':
                current_app.logger.info(f"Payment notification sent for {reference_number}")
            else:
                current_app.logger.error(f"Failed to send payment notification: {result['message']}")
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error sending payment notification: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def send_security_alert(phone_number, alert_type, details):
        """
        Send security alert SMS to administrators
        
        Args:
            phone_number (str): Admin phone number
            alert_type (str): Type of security alert
            details (str): Alert details
        """
        try:
            message = (
                f"🔒 SECURITY ALERT\n"
                f"Type: {alert_type}\n"
                f"Details: {details}\n"
                f"Time: {datetime.utcnow().strftime('%H:%M %d/%m/%Y')}\n"
                f"Please investigate immediately."
            )
            
            result = SMSService._send_sms(phone_number, message)
            
            if result['status'] == 'success':
                current_app.logger.info(f"Security alert sent: {alert_type}")
            else:
                current_app.logger.error(f"Failed to send security alert: {result['message']}")
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error sending security alert: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def send_bulk_sms(recipients, message, sender_id=None):
        """
        Send bulk SMS to multiple recipients
        
        Args:
            recipients (list): List of phone numbers
            message (str): SMS message content
            sender_id (str): Sender ID (optional)
        
        Returns:
            dict: Bulk SMS results
        """
        try:
            results = []
            
            for phone_number in recipients:
                result = SMSService._send_sms(phone_number, message, sender_id)
                results.append({
                    'phone_number': phone_number,
                    'status': result['status'],
                    'message_id': result.get('message_id')
                })
            
            success_count = sum(1 for r in results if r['status'] == 'success')
            
            current_app.logger.info(f"Bulk SMS sent: {success_count}/{len(recipients)} successful")
            
            return {
                'status': 'completed',
                'total_sent': len(recipients),
                'successful': success_count,
                'failed': len(recipients) - success_count,
                'results': results
            }
            
        except Exception as e:
            current_app.logger.error(f"Error sending bulk SMS: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def get_delivery_status(message_id):
        """
        Get SMS delivery status from Africa's Talking
        
        Args:
            message_id (str): Message ID from SMS API
        
        Returns:
            dict: Delivery status information
        """
        config = SMSService._get_api_config()
        
        if not config['api_key'] or not message_id:
            return {'status': 'error', 'message': 'Invalid parameters'}
        
        try:
            url = f"https://api.sandbox.africastalking.com/version1/messaging/delivery-reports"
            
            headers = {
                'Accept': 'application/json',
                'apiKey': config['api_key']
            }
            
            params = {
                'username': config['username'],
                'messageId': message_id
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return {'status': 'success', 'delivery_status': result}
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"SMS delivery status error: {e}")
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            current_app.logger.error(f"Error getting delivery status: {e}")
            return {'status': 'error', 'message': str(e)}