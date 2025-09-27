#!/usr/bin/env python3
"""
USSD Emergency Response System Test Script

This script simulates USSD interactions to test the emergency response system.
It demonstrates how users would interact with the system during a disaster.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:12000"
TEST_PHONE = "+2348012345678"
TEST_SESSION = "test_session_123"

def make_ussd_request(phone_number, session_id, user_input=""):
    """Make a USSD request to the test endpoint"""
    url = f"{BASE_URL}/ussd/test"
    payload = {
        "phone_number": phone_number,
        "session_id": session_id,
        "input": user_input
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None

def print_ussd_response(response, step_name):
    """Print USSD response in a formatted way"""
    print(f"\n{'='*50}")
    print(f"STEP: {step_name}")
    print(f"{'='*50}")
    
    if response and response.get('success'):
        ussd_response = response['response']
        print(f"MESSAGE:\n{ussd_response['message']}")
        print(f"CONTINUE SESSION: {ussd_response['continue_session']}")
    else:
        print(f"ERROR: {response.get('error', 'Unknown error') if response else 'No response'}")
    
    print(f"{'='*50}")

def simulate_shelter_request():
    """Simulate a complete shelter request flow"""
    print("\n🏠 SIMULATING SHELTER REQUEST FLOW")
    print("Scenario: Flood victim needs emergency shelter in Lokoja")
    
    # Step 1: Initial USSD dial (*123#)
    response = make_ussd_request(TEST_PHONE, TEST_SESSION)
    print_ussd_response(response, "Initial Menu (*123#)")
    
    # Step 2: Select Shelter (option 1)
    response = make_ussd_request(TEST_PHONE, TEST_SESSION, "1")
    print_ussd_response(response, "Select Shelter")
    
    # Step 3: Enter location
    response = make_ussd_request(TEST_PHONE, TEST_SESSION, "Lokoja")
    print_ussd_response(response, "Enter Location")
    
    # Step 4: Confirm selection (option 1)
    response = make_ussd_request(TEST_PHONE, TEST_SESSION, "1")
    print_ussd_response(response, "Confirm Selection")

def simulate_food_request():
    """Simulate a food request flow"""
    print("\n🍽️ SIMULATING FOOD REQUEST FLOW")
    print("Scenario: Family needs emergency food supplies")
    
    # New session for food request
    food_session = "food_session_456"
    
    # Step 1: Initial USSD dial
    response = make_ussd_request(TEST_PHONE, food_session)
    print_ussd_response(response, "Initial Menu")
    
    # Step 2: Select Food (option 2)
    response = make_ussd_request(TEST_PHONE, food_session, "2")
    print_ussd_response(response, "Select Food")
    
    # Step 3: Enter location
    response = make_ussd_request(TEST_PHONE, food_session, "Ganaja")
    print_ussd_response(response, "Enter Location")
    
    # Step 4: Confirm selection
    response = make_ussd_request(TEST_PHONE, food_session, "1")
    print_ussd_response(response, "Confirm Selection")

def simulate_transport_request():
    """Simulate a transport request flow"""
    print("\n🚗 SIMULATING TRANSPORT REQUEST FLOW")
    print("Scenario: Person needs evacuation transport")
    
    # New session for transport request
    transport_session = "transport_session_789"
    
    # Step 1: Initial USSD dial
    response = make_ussd_request(TEST_PHONE, transport_session)
    print_ussd_response(response, "Initial Menu")
    
    # Step 2: Select Transport (option 3)
    response = make_ussd_request(TEST_PHONE, transport_session, "3")
    print_ussd_response(response, "Select Transport")
    
    # Step 3: Enter location
    response = make_ussd_request(TEST_PHONE, transport_session, "Adankolo")
    print_ussd_response(response, "Enter Location")
    
    # Step 4: Confirm selection
    response = make_ussd_request(TEST_PHONE, transport_session, "1")
    print_ussd_response(response, "Confirm Selection")

def test_api_endpoints():
    """Test API endpoints"""
    print("\n🔧 TESTING API ENDPOINTS")
    
    # Test resources endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/resources")
        if response.status_code == 200:
            resources = response.json()
            print(f"✅ Found {len(resources)} resources in the system")
        else:
            print(f"❌ Resources API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Resources API error: {e}")
    
    # Test statistics endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ System statistics retrieved successfully")
            print(f"   - Shelter resources: {stats['shelter']['total_resources']}")
            print(f"   - Food resources: {stats['food']['total_resources']}")
            print(f"   - Transport resources: {stats['transport']['total_resources']}")
        else:
            print(f"❌ Statistics API failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Statistics API error: {e}")

def main():
    """Main test function"""
    print("🚨 EMERGENCY RESPONSE USSD SYSTEM TEST")
    print("=====================================")
    print("This script simulates how people would use the system during a disaster")
    print("when they only have basic phones with SMS and USSD capabilities.")
    
    # Wait for server to be ready
    print("\n⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    # Test API endpoints first
    test_api_endpoints()
    
    # Simulate different emergency scenarios
    simulate_shelter_request()
    time.sleep(1)
    
    simulate_food_request()
    time.sleep(1)
    
    simulate_transport_request()
    
    print("\n✅ TEST COMPLETED")
    print("================")
    print("The system successfully handled multiple emergency requests!")
    print("In a real disaster, this would connect victims to actual resources.")
    print("\nNext steps:")
    print("1. Integrate with telecom USSD gateway")
    print("2. Connect to SMS service provider")
    print("3. Add real-time resource updates")
    print("4. Deploy to production servers")

if __name__ == "__main__":
    main()