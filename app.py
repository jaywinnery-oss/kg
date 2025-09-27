from app import create_app, db
from app.models import User, Resource, ResourceType, EmergencyRequest, USSDSession
from flask_migrate import upgrade
import os

USSD_SERVICE_CODE = os.getenv("USSD_SERVICE_CODE", "*384#")
USSD_CHANNEL = os.getenv("USSD_CHANNEL", "17925")

app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Resource': Resource,
        'ResourceType': ResourceType,
        'EmergencyRequest': EmergencyRequest,
        'USSDSession': USSDSession
    }

@app.route('/')
def index():
    return {
        'message': 'Emergency Response USSD System',
        'version': '1.0.0',
        'endpoints': {
            'ussd_callback': '/ussd/callback',
            'ussd_test': '/ussd/test',
            'admin_dashboard': '/admin/',
            'api_resources': '/api/resources',
            'api_requests': '/api/requests'
        }
    }

def init_db():
    """Initialize database with sample data"""
    db.create_all()
    
    # Check if we already have sample data
    if Resource.query.first():
        return
    
    # Add sample resources
    sample_resources = [
        # Shelter resources
        Resource(
            name="Lokoja Emergency Shelter",
            description="Emergency shelter with 200 bed capacity",
            resource_type=ResourceType.SHELTER,
            location="Lokoja, Kogi State",
            latitude=7.8023,
            longitude=6.7343,
            total_capacity=200,
            available_capacity=150,
            contact_person="John Adamu",
            contact_phone="+2348012345678",
            organization="Kogi State Emergency Management Agency"
        ),
        Resource(
            name="Confluence University Hostel",
            description="Temporary accommodation for flood victims",
            resource_type=ResourceType.SHELTER,
            location="Osara, Kogi State",
            latitude=7.8500,
            longitude=6.7000,
            total_capacity=100,
            available_capacity=80,
            contact_person="Dr. Sarah Ibrahim",
            contact_phone="+2348023456789",
            organization="Confluence University"
        ),
        
        # Food resources
        Resource(
            name="Red Cross Food Distribution Center",
            description="Emergency food supplies and hot meals",
            resource_type=ResourceType.FOOD,
            location="Ganaja, Lokoja",
            latitude=7.8100,
            longitude=6.7400,
            total_capacity=500,
            available_capacity=300,
            contact_person="Fatima Usman",
            contact_phone="+2348034567890",
            organization="Nigerian Red Cross Society"
        ),
        Resource(
            name="Community Kitchen - Adankolo",
            description="Free meals for disaster victims",
            resource_type=ResourceType.FOOD,
            location="Adankolo, Lokoja",
            latitude=7.7900,
            longitude=6.7200,
            total_capacity=200,
            available_capacity=150,
            contact_person="Musa Yakubu",
            contact_phone="+2348045678901",
            organization="Adankolo Community Association"
        ),
        
        # Transport resources
        Resource(
            name="Emergency Evacuation Buses",
            description="Free transport to higher ground",
            resource_type=ResourceType.TRANSPORT,
            location="Lokoja Motor Park",
            latitude=7.8000,
            longitude=6.7300,
            total_capacity=50,
            available_capacity=30,
            contact_person="Ibrahim Mohammed",
            contact_phone="+2348056789012",
            organization="Kogi State Transport Authority"
        ),
        Resource(
            name="Medical Emergency Transport",
            description="Ambulance services for medical emergencies",
            resource_type=ResourceType.TRANSPORT,
            location="Federal Medical Centre Lokoja",
            latitude=7.8200,
            longitude=6.7500,
            total_capacity=10,
            available_capacity=8,
            contact_person="Dr. Amina Hassan",
            contact_phone="+2348067890123",
            organization="Federal Medical Centre"
        )
    ]
    
    for resource in sample_resources:
        db.session.add(resource)
    
    db.session.commit()
    print("Sample data added successfully!")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    
    app.run(
        host='0.0.0.0',
        port=12001,
        debug=True
    )