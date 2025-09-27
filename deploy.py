#!/usr/bin/env python3
"""
Emergency Response System Deployment Script

This script helps deploy the USSD-based emergency response system
to production environments.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking deployment requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        return False
    
    # Check if app.py exists
    if not Path("app.py").exists():
        print("❌ app.py not found")
        return False
    
    print("✅ All requirements met")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_database():
    """Initialize the database"""
    print("🗄️ Setting up database...")
    try:
        # Import and initialize database
        from app import app, db
        with app.app_context():
            db.create_all()
            print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to setup database: {e}")
        return False

def create_systemd_service():
    """Create systemd service file for production deployment"""
    service_content = f"""[Unit]
Description=Emergency Response USSD System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory={os.getcwd()}
Environment=PATH={os.getcwd()}/venv/bin
ExecStart={sys.executable} app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_file = "/etc/systemd/system/emergency-response.service"
    print(f"📝 Creating systemd service file: {service_file}")
    
    try:
        with open("emergency-response.service", "w") as f:
            f.write(service_content)
        print("✅ Service file created (copy to /etc/systemd/system/ manually)")
        print("   sudo cp emergency-response.service /etc/systemd/system/")
        print("   sudo systemctl enable emergency-response")
        print("   sudo systemctl start emergency-response")
        return True
    except Exception as e:
        print(f"❌ Failed to create service file: {e}")
        return False

def create_nginx_config():
    """Create nginx configuration for reverse proxy"""
    nginx_config = """server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:12001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/your/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
"""
    
    print("🌐 Creating nginx configuration...")
    try:
        with open("emergency-response-nginx.conf", "w") as f:
            f.write(nginx_config)
        print("✅ Nginx config created (copy to /etc/nginx/sites-available/)")
        print("   sudo cp emergency-response-nginx.conf /etc/nginx/sites-available/emergency-response")
        print("   sudo ln -s /etc/nginx/sites-available/emergency-response /etc/nginx/sites-enabled/")
        print("   sudo nginx -t && sudo systemctl reload nginx")
        return True
    except Exception as e:
        print(f"❌ Failed to create nginx config: {e}")
        return False

def create_env_template():
    """Create environment variables template"""
    env_template = """# Emergency Response System Environment Variables

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost/emergency_response

# SMS Service Configuration
SMS_API_KEY=your-sms-api-key
SMS_GATEWAY_URL=https://api.sms-provider.com/send

# USSD Gateway Configuration
USSD_GATEWAY_URL=https://api.ussd-provider.com/callback
USSD_SERVICE_CODE=*384*68503#

# Security
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Monitoring
SENTRY_DSN=your-sentry-dsn-here
"""
    
    print("🔧 Creating environment template...")
    try:
        with open(".env.template", "w") as f:
            f.write(env_template)
        print("✅ Environment template created (.env.template)")
        print("   Copy to .env and fill in your actual values")
        return True
    except Exception as e:
        print(f"❌ Failed to create environment template: {e}")
        return False

def run_tests():
    """Run system tests"""
    print("🧪 Running system tests...")
    try:
        # Run the test script
        result = subprocess.run([sys.executable, "test_ussd.py"], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print(f"❌ Tests failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out")
        return False
    except FileNotFoundError:
        print("⚠️ Test script not found, skipping tests")
        return True

def print_deployment_checklist():
    """Print deployment checklist"""
    print("\n" + "="*60)
    print("🚀 DEPLOYMENT CHECKLIST")
    print("="*60)
    
    checklist = [
        "✅ Set up production server (Ubuntu 20.04+ recommended)",
        "✅ Install Python 3.8+, pip, and virtualenv",
        "✅ Install PostgreSQL and create database",
        "✅ Install nginx for reverse proxy",
        "✅ Configure firewall (allow ports 80, 443)",
        "✅ Set up SSL certificate (Let's Encrypt recommended)",
        "✅ Configure environment variables (.env file)",
        "✅ Set up USSD gateway with telecom provider",
        "✅ Configure SMS service provider",
        "✅ Set up monitoring and logging",
        "✅ Configure backup strategy",
        "✅ Test emergency response flows",
        "✅ Train admin users on dashboard",
        "✅ Coordinate with emergency services",
        "✅ Plan disaster response protocols"
    ]
    
    for item in checklist:
        print(f"  {item}")
    
    print("\n" + "="*60)
    print("🔗 INTEGRATION PARTNERS")
    print("="*60)
    print("  📡 Telecom Providers:")
    print("    - MTN Nigeria: https://developer.mtn.com/")
    print("    - Airtel Nigeria: https://developers.airtel.africa/")
    print("    - Glo Mobile: Contact business development")
    print("    - 9mobile: Contact API team")
    
    print("\n  📱 SMS Providers:")
    print("    - Twilio: https://www.twilio.com/")
    print("    - Nexmo/Vonage: https://www.vonage.com/")
    print("    - BulkSMS Nigeria: https://www.bulksms.com/")
    print("    - SmartSMSSolutions: https://smartsmssolutions.com/")
    
    print("\n  🏛️ Government Agencies:")
    print("    - NEMA: https://nema.gov.ng/")
    print("    - State Emergency Management Agencies")
    print("    - Local Government Emergency Coordinators")

def main():
    """Main deployment function"""
    print("🚨 EMERGENCY RESPONSE SYSTEM DEPLOYMENT")
    print("======================================")
    print("This script will help you deploy the USSD-based emergency response system")
    print("to a production environment.\n")
    
    # Check requirements
    if not check_requirements():
        print("❌ Deployment failed: Requirements not met")
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Deployment failed: Could not install dependencies")
        return False
    
    # Setup database
    if not setup_database():
        print("❌ Deployment failed: Database setup failed")
        return False
    
    # Run tests
    if not run_tests():
        print("⚠️ Warning: Some tests failed, but continuing deployment")
    
    # Create deployment files
    create_systemd_service()
    create_nginx_config()
    create_env_template()
    
    # Print checklist
    print_deployment_checklist()
    
    print("\n✅ DEPLOYMENT PREPARATION COMPLETE!")
    print("===================================")
    print("Your emergency response system is ready for production deployment.")
    print("Follow the checklist above to complete the deployment process.")
    print("\nFor support, contact: support@emergency-response.ng")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)