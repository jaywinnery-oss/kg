"""
Emergency Response USSD System - Main Application
Secure emergency response system with USSD/SMS integration
"""
from app import create_app, db
from app.models import (
    User, Resource, ResourceType, EmergencyRequest, USSDSession,
    Provider, AuditLog, Payment, UserRole, encrypt_data
)
from flask_migrate import upgrade
import os

# Configuration from environment
USSD_SERVICE_CODE = os.getenv("USSD_SERVICE_CODE", "*384#")
USSD_CHANNEL = os.getenv("USSD_CHANNEL", "17925")

# Create application
app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    """Make shell context for flask shell command"""
    return {
        'db': db,
        'User': User,
        'Resource': Resource,
        'ResourceType': ResourceType,
        'EmergencyRequest': EmergencyRequest,
        'USSDSession': USSDSession,
        'Provider': Provider,
        'AuditLog': AuditLog,
        'Payment': Payment,
        'UserRole': UserRole
    }

def init_db():
    """Initialize database with sample data"""
    print("Initializing database...")
    db.create_all()
    
    # Check if we already have sample data
    if Resource.query.first():
        print("Sample data already exists, skipping initialization.")
        return
    
    print("Creating sample providers and resources...")
    
    # Create sample providers first
    sample_providers = [
        {
            'user_data': {
                'phone': '+2348012345678',
                'name': 'John Adamu',
                'role': UserRole.GOVERNMENT
            },
            'provider_data': {
                'organization_name': 'Kogi State Emergency Management Agency',
                'verification_status': 'verified'
            }
        },
        {
            'user_data': {
                'phone': '+2348023456789',
                'name': 'Dr. Sarah Ibrahim',
                'role': UserRole.NGO
            },
            'provider_data': {
                'organization_name': 'Confluence University',
                'verification_status': 'verified'
            }
        },
        {
            'user_data': {
                'phone': '+2348034567890',
                'name': 'Fatima Usman',
                'role': UserRole.NGO
            },
            'provider_data': {
                'organization_name': 'Nigerian Red Cross Society',
                'verification_status': 'verified'
            }
        }
    ]
    
    providers = []
    for provider_info in sample_providers:
        # Create user
        user = User(
            provider_info['user_data']['phone'],
            provider_info['user_data']['name'],
            provider_info['user_data']['role']
        )
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Create provider
        provider = Provider(
            user_id=user.id,
            organization_name=provider_info['provider_data']['organization_name'],
            encrypted_contact_person=encrypt_data(provider_info['user_data']['name']),
            encrypted_email=encrypt_data(f"contact@{provider_info['provider_data']['organization_name'].lower().replace(' ', '')}.ng"),
            verification_status=provider_info['provider_data']['verification_status']
        )
        db.session.add(provider)
        db.session.flush()
        providers.append(provider)
    
    # Add sample resources
    sample_resources = [
        # Shelter resources
        {
            'provider_id': providers[0].id,  # SEMA
            'name': "Lokoja Emergency Shelter",
            'description': "Emergency shelter with 200 bed capacity",
            'resource_type': ResourceType.SHELTER,
            'location': "Lokoja, Kogi State",
            'latitude': 7.8023,
            'longitude': 6.7343,
            'total_capacity': 200,
            'available_capacity': 150,
            'contact_phone': '+2348012345678',
            'price_per_unit': 0.0
        },
        {
            'provider_id': providers[1].id,  # University
            'name': "Confluence University Hostel",
            'description': "Temporary accommodation for flood victims",
            'resource_type': ResourceType.SHELTER,
            'location': "Osara, Kogi State",
            'latitude': 7.8500,
            'longitude': 6.7000,
            'total_capacity': 100,
            'available_capacity': 80,
            'contact_phone': '+2348023456789',
            'price_per_unit': 500.0  # Paid service
        },
        
        # Food resources
        {
            'provider_id': providers[2].id,  # Red Cross
            'name': "Red Cross Food Distribution Center",
            'description': "Emergency food supplies and hot meals",
            'resource_type': ResourceType.FOOD,
            'location': "Ganaja, Lokoja",
            'latitude': 7.8100,
            'longitude': 6.7400,
            'total_capacity': 500,
            'available_capacity': 300,
            'contact_phone': '+2348034567890',
            'price_per_unit': 0.0
        },
        {
            'provider_id': providers[1].id,  # University
            'name': "Community Kitchen - Adankolo",
            'description': "Free meals for disaster victims",
            'resource_type': ResourceType.FOOD,
            'location': "Adankolo, Lokoja",
            'latitude': 7.7900,
            'longitude': 6.7200,
            'total_capacity': 200,
            'available_capacity': 150,
            'contact_phone': '+2348045678901',
            'price_per_unit': 0.0
        },
        
        # Transport resources
        {
            'provider_id': providers[0].id,  # SEMA
            'name': "Emergency Evacuation Buses",
            'description': "Free transport to higher ground",
            'resource_type': ResourceType.TRANSPORT,
            'location': "Lokoja Motor Park",
            'latitude': 7.8000,
            'longitude': 6.7300,
            'total_capacity': 50,
            'available_capacity': 30,
            'contact_phone': '+2348056789012',
            'price_per_unit': 0.0
        },
        {
            'provider_id': providers[0].id,  # SEMA
            'name': "Medical Emergency Transport",
            'description': "Ambulance services for medical emergencies",
            'resource_type': ResourceType.TRANSPORT,
            'location': "Federal Medical Centre Lokoja",
            'latitude': 7.8200,
            'longitude': 6.7500,
            'total_capacity': 10,
            'available_capacity': 8,
            'contact_phone': '+2348067890123',
            'price_per_unit': 1000.0  # Paid service
        }
    ]
    
    for resource_data in sample_resources:
        resource = Resource(
            provider_id=resource_data['provider_id'],
            name=resource_data['name'],
            description=resource_data['description'],
            resource_type=resource_data['resource_type'],
            location=resource_data['location'],
            latitude=resource_data['latitude'],
            longitude=resource_data['longitude'],
            total_capacity=resource_data['total_capacity'],
            available_capacity=resource_data['available_capacity'],
            price_per_unit=resource_data['price_per_unit']
        )
        
        # Encrypt contact phone
        if resource_data.get('contact_phone'):
            resource.encrypted_contact_phone = encrypt_data(resource_data['contact_phone'])
        
        db.session.add(resource)
    
    # Create admin user
    admin_user = User('+2348000000000', 'System Admin', UserRole.ADMIN)
    db.session.add(admin_user)
    
    db.session.commit()
    print("Sample data added successfully!")
    print(f"USSD Service Code: {USSD_SERVICE_CODE}")
    print(f"USSD Channel: {USSD_CHANNEL}")
    print("System ready for testing!")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    
    port = int(os.getenv('PORT', 8080))
    print(f"Starting Emergency Response System on port {port}...")
    print(f"USSD Callback URL: http://localhost:{port}/ussd/callback")
    print(f"Admin Dashboard: http://localhost:{port}/admin/")
    print(f"API Documentation: http://localhost:{port}/docs")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )