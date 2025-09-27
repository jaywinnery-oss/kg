#!/usr/bin/env python3
"""
Complete System Test - Emergency Response USSD System
Tests all major functionality including USSD flow, security features, and API endpoints
"""

import requests
import json
import time
from urllib.parse import quote

# Configuration
BASE_URL = "http://localhost:8080"
TEST_PHONE = "+2348012345678"

def print_header(title):
    """Print formatted test section header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_step(step, description):
    """Print formatted test step"""
    print(f"\n{step}. {description}")
    print("-" * 40)

def test_system_status():
    """Test system status endpoint"""
    print_header("SYSTEM STATUS TEST")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ System Status: {data.get('status', 'unknown')}")
            print(f"📊 Total Resources: {data.get('statistics', {}).get('total_resources', 0)}")
            print(f"🔧 USSD Service Code: {data.get('ussd_service', {}).get('service_code', 'N/A')}")
            print(f"🛡️ Security Features: {len(data.get('security_features', []))}")
        else:
            print(f"❌ System status check failed")
            
    except Exception as e:
        print(f"❌ Error checking system status: {e}")

def test_ussd_flow():
    """Test complete USSD flow"""
    print_header("USSD FLOW TEST")
    
    session_id = f"test_{int(time.time())}"
    
    # Step 1: Initial USSD request
    print_step(1, "Testing initial USSD menu")
    try:
        response = requests.post(f"{BASE_URL}/ussd/callback", data={
            'sessionId': session_id,
            'serviceCode': '*384*',
            'phoneNumber': TEST_PHONE,
            'text': ''
        })
        
        print(f"Response: {response.text}")
        if "Emergency Response System" in response.text:
            print("✅ Initial menu loaded successfully")
        else:
            print("❌ Initial menu failed")
            
    except Exception as e:
        print(f"❌ Error in initial USSD request: {e}")
    
    # Step 2: Select shelter service
    print_step(2, "Selecting shelter service (option 1)")
    try:
        response = requests.post(f"{BASE_URL}/ussd/callback", data={
            'sessionId': session_id,
            'serviceCode': '*384*',
            'phoneNumber': TEST_PHONE,
            'text': '1'
        })
        
        print(f"Response: {response.text}")
        if "You selected: Shelter" in response.text:
            print("✅ Shelter service selected successfully")
        else:
            print("❌ Shelter service selection failed")
            
    except Exception as e:
        print(f"❌ Error selecting shelter service: {e}")
    
    # Step 3: Enter location
    print_step(3, "Entering location (Lokoja)")
    try:
        response = requests.post(f"{BASE_URL}/ussd/callback", data={
            'sessionId': session_id,
            'serviceCode': '*384*',
            'phoneNumber': TEST_PHONE,
            'text': '1*Lokoja'
        })
        
        print(f"Response: {response.text}")
        if "Available shelter near Lokoja" in response.text:
            print("✅ Location-based resources found")
        else:
            print("❌ Location-based search failed")
            
    except Exception as e:
        print(f"❌ Error in location search: {e}")
    
    # Step 4: Select resource
    print_step(4, "Selecting first available resource")
    try:
        response = requests.post(f"{BASE_URL}/ussd/callback", data={
            'sessionId': session_id,
            'serviceCode': '*384*',
            'phoneNumber': TEST_PHONE,
            'text': '1*Lokoja*1'
        })
        
        print(f"Response: {response.text}")
        if "Confirm your request" in response.text:
            print("✅ Resource selection and confirmation screen shown")
        else:
            print("❌ Resource selection failed")
            
    except Exception as e:
        print(f"❌ Error selecting resource: {e}")
    
    # Step 5: Confirm request
    print_step(5, "Confirming emergency request")
    try:
        response = requests.post(f"{BASE_URL}/ussd/callback", data={
            'sessionId': session_id,
            'serviceCode': '*384*',
            'phoneNumber': TEST_PHONE,
            'text': '1*Lokoja*1*1'
        })
        
        print(f"Response: {response.text}")
        if "Request confirmed!" in response.text and "Reference:" in response.text:
            print("✅ Emergency request confirmed successfully")
            # Extract reference number
            lines = response.text.split('\n')
            for line in lines:
                if "Reference:" in line:
                    ref_number = line.split("Reference:")[1].strip()
                    print(f"📋 Reference Number: {ref_number}")
                    return ref_number
        else:
            print("❌ Request confirmation failed")
            
    except Exception as e:
        print(f"❌ Error confirming request: {e}")
    
    return None

def test_rate_limiting():
    """Test rate limiting functionality"""
    print_header("RATE LIMITING TEST")
    
    print_step(1, "Testing USSD rate limiting (multiple rapid requests)")
    
    session_base = f"rate_test_{int(time.time())}"
    successful_requests = 0
    rate_limited_requests = 0
    
    # Send multiple requests rapidly
    for i in range(5):
        try:
            response = requests.post(f"{BASE_URL}/ussd/callback", data={
                'sessionId': f"{session_base}_{i}",
                'serviceCode': '*384*',
                'phoneNumber': TEST_PHONE,
                'text': ''
            })
            
            if response.status_code == 200:
                successful_requests += 1
                print(f"  Request {i+1}: ✅ Success")
            elif response.status_code == 429:
                rate_limited_requests += 1
                print(f"  Request {i+1}: 🚫 Rate Limited")
            else:
                print(f"  Request {i+1}: ❓ Status {response.status_code}")
                
        except Exception as e:
            print(f"  Request {i+1}: ❌ Error: {e}")
        
        time.sleep(0.5)  # Small delay between requests
    
    print(f"\n📊 Results:")
    print(f"  Successful requests: {successful_requests}")
    print(f"  Rate limited requests: {rate_limited_requests}")
    
    if rate_limited_requests > 0:
        print("✅ Rate limiting is working correctly")
    else:
        print("⚠️ Rate limiting may not be configured properly")

def test_api_endpoints():
    """Test API endpoints"""
    print_header("API ENDPOINTS TEST")
    
    # Test public endpoints
    print_step(1, "Testing public API endpoints")
    
    endpoints = [
        ("/", "System status"),
        ("/api/stats", "System statistics"),
    ]
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"  {endpoint} ({description}): Status {response.status_code}")
            
            if response.status_code == 200:
                print(f"    ✅ Success")
            else:
                print(f"    ❌ Failed")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Test protected endpoints (should require authentication)
    print_step(2, "Testing protected endpoints (should require auth)")
    
    protected_endpoints = [
        ("/admin/", "Admin dashboard"),
        ("/provider/", "Provider portal"),
        ("/api/resources", "Resource management"),
    ]
    
    for endpoint, description in protected_endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"  {endpoint} ({description}): Status {response.status_code}")
            
            if response.status_code == 401:
                print(f"    ✅ Correctly requires authentication")
            elif response.status_code == 403:
                print(f"    ✅ Correctly requires authorization")
            else:
                print(f"    ⚠️ May not be properly protected")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")

def test_security_features():
    """Test security features"""
    print_header("SECURITY FEATURES TEST")
    
    print_step(1, "Testing input validation")
    
    # Test malicious inputs
    malicious_inputs = [
        "<script>alert('xss')</script>",
        "'; DROP TABLE users; --",
        "../../../etc/passwd",
        "{{7*7}}",
    ]
    
    for malicious_input in malicious_inputs:
        try:
            response = requests.post(f"{BASE_URL}/ussd/callback", data={
                'sessionId': 'security_test',
                'serviceCode': '*384*',
                'phoneNumber': TEST_PHONE,
                'text': malicious_input
            })
            
            # Check if malicious input is reflected in response
            if malicious_input in response.text:
                print(f"  ⚠️ Potential XSS vulnerability with input: {malicious_input[:20]}...")
            else:
                print(f"  ✅ Input properly sanitized: {malicious_input[:20]}...")
                
        except Exception as e:
            print(f"  ❌ Error testing input: {e}")
    
    print_step(2, "Testing HTTP security headers")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        headers = response.headers
        
        security_headers = [
            ('X-Content-Type-Options', 'nosniff'),
            ('X-Frame-Options', 'DENY'),
            ('X-XSS-Protection', '1; mode=block'),
        ]
        
        for header, expected in security_headers:
            if header in headers:
                print(f"  ✅ {header}: {headers[header]}")
            else:
                print(f"  ⚠️ Missing security header: {header}")
                
    except Exception as e:
        print(f"  ❌ Error checking headers: {e}")

def test_provider_registration():
    """Test provider registration"""
    print_header("PROVIDER REGISTRATION TEST")
    
    print_step(1, "Testing provider registration form")
    
    try:
        response = requests.get(f"{BASE_URL}/provider/register")
        print(f"Registration form status: {response.status_code}")
        
        if response.status_code == 200 and "Provider Registration" in response.text:
            print("✅ Registration form loads correctly")
        else:
            print("❌ Registration form failed to load")
            
    except Exception as e:
        print(f"❌ Error loading registration form: {e}")
    
    print_step(2, "Testing provider registration submission")
    
    test_data = {
        'organization_name': 'Test Emergency Services',
        'contact_person': 'John Test',
        'email': 'test@example.com',
        'phone': '+2348099999999',
        'organization_type': 'ngo',
        'services': 'Emergency shelter and food distribution',
        'coverage_area': 'Lokoja, Kogi State',
        'terms': 'on'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/provider/register", data=test_data)
        print(f"Registration submission status: {response.status_code}")
        
        if response.status_code == 201:
            print("✅ Provider registration successful")
        elif response.status_code == 400:
            print("⚠️ Registration validation failed (expected for test data)")
        else:
            print(f"❓ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error submitting registration: {e}")

def generate_test_report():
    """Generate comprehensive test report"""
    print_header("TEST REPORT SUMMARY")
    
    print("🧪 Emergency Response USSD System - Test Results")
    print(f"📅 Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"📱 Test Phone: {TEST_PHONE}")
    
    print("\n📋 Tests Completed:")
    print("  ✅ System Status Check")
    print("  ✅ Complete USSD Flow")
    print("  ✅ Rate Limiting")
    print("  ✅ API Endpoints")
    print("  ✅ Security Features")
    print("  ✅ Provider Registration")
    
    print("\n🔧 System Configuration:")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"  USSD Service Code: {data.get('ussd_service', {}).get('service_code', 'N/A')}")
            print(f"  Total Resources: {data.get('statistics', {}).get('total_resources', 0)}")
            print(f"  Security Features: {len(data.get('security_features', []))}")
    except:
        print("  Unable to retrieve system configuration")
    
    print("\n🚀 Next Steps:")
    print("  1. Configure Africa's Talking credentials")
    print("  2. Set up ngrok for webhook exposure")
    print("  3. Test with real USSD service code")
    print("  4. Deploy to production environment")
    
    print("\n📞 For Support:")
    print("  📧 Email: support@emergency-response.ng")
    print("  📚 Documentation: README.md, DEPLOYMENT.md, SECURITY.md")

def main():
    """Run all tests"""
    print("🚨 Emergency Response USSD System - Complete Test Suite")
    print("=" * 60)
    
    # Run all tests
    test_system_status()
    reference_number = test_ussd_flow()
    test_rate_limiting()
    test_api_endpoints()
    test_security_features()
    test_provider_registration()
    
    # Generate report
    generate_test_report()
    
    print(f"\n{'='*60}")
    print("🎉 All tests completed!")
    print("Check the output above for detailed results.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()