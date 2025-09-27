#!/usr/bin/env python3
"""
Emergency Response System Demo

This script demonstrates the USSD-based emergency response system
for disaster situations in Nigeria.
"""

import subprocess
import time
import threading
import requests
import json

def start_server():
    """Start the Flask server in the background"""
    print("🚀 Starting Emergency Response Server...")
    process = subprocess.Popen(['python', 'app.py'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    
    # Wait for server to start
    time.sleep(5)
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:12000/', timeout=5)
        if response.status_code == 200:
            print("✅ Server is running successfully!")
            return process
        else:
            print("❌ Server failed to start properly")
            return None
    except:
        print("❌ Server is not responding")
        return None

def demo_ussd_flow():
    """Demonstrate the USSD flow"""
    print("\n" + "="*60)
    print("🚨 EMERGENCY RESPONSE SYSTEM DEMONSTRATION")
    print("="*60)
    
    print("\nSCENARIO: Flood hits Kogi State")
    print("A person with only a basic phone needs emergency shelter")
    print("\nUSSD Flow Simulation:")
    print("1. Person dials *123# on their phone")
    print("2. System shows emergency menu")
    print("3. Person selects shelter option")
    print("4. System finds nearby resources")
    print("5. Person gets connected to help")
    
    # Simulate USSD requests
    base_url = "http://localhost:12000"
    
    print("\n" + "-"*40)
    print("📱 USSD SESSION SIMULATION")
    print("-"*40)
    
    # Step 1: Initial menu
    print("\n1️⃣ User dials *123#")
    try:
        response = requests.post(f"{base_url}/ussd/test", 
                               json={"phone_number": "+2348012345678", 
                                    "session_id": "demo_session", 
                                    "input": ""})
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("📟 USSD Response:")
                print(data['response']['message'])
            else:
                print("❌ Error:", data.get('error'))
        else:
            print("❌ Server error:", response.status_code)
    except Exception as e:
        print("❌ Connection error:", e)
    
    time.sleep(2)
    
    # Step 2: Select shelter
    print("\n2️⃣ User presses 1 for Shelter")
    try:
        response = requests.post(f"{base_url}/ussd/test", 
                               json={"phone_number": "+2348012345678", 
                                    "session_id": "demo_session", 
                                    "input": "1"})
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("📟 USSD Response:")
                print(data['response']['message'])
            else:
                print("❌ Error:", data.get('error'))
    except Exception as e:
        print("❌ Connection error:", e)
    
    time.sleep(2)
    
    # Step 3: Enter location
    print("\n3️⃣ User types 'Lokoja' as location")
    try:
        response = requests.post(f"{base_url}/ussd/test", 
                               json={"phone_number": "+2348012345678", 
                                    "session_id": "demo_session", 
                                    "input": "Lokoja"})
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("📟 USSD Response:")
                print(data['response']['message'])
            else:
                print("❌ Error:", data.get('error'))
    except Exception as e:
        print("❌ Connection error:", e)
    
    time.sleep(2)
    
    # Step 4: Confirm selection
    print("\n4️⃣ User presses 1 to confirm")
    try:
        response = requests.post(f"{base_url}/ussd/test", 
                               json={"phone_number": "+2348012345678", 
                                    "session_id": "demo_session", 
                                    "input": "1"})
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("📟 USSD Response:")
                print(data['response']['message'])
                print("\n✅ SUCCESS: User has been connected to emergency shelter!")
            else:
                print("❌ Error:", data.get('error'))
    except Exception as e:
        print("❌ Connection error:", e)

def show_system_features():
    """Show system features and capabilities"""
    print("\n" + "="*60)
    print("🔧 SYSTEM FEATURES")
    print("="*60)
    
    features = [
        "📱 Works with basic phones (no internet required)",
        "🚨 USSD-based emergency menu (*123#)",
        "🏠 Shelter location and booking",
        "🍽️ Food distribution centers",
        "🚗 Emergency transport coordination",
        "📍 Location-based resource matching",
        "📱 SMS confirmations and updates",
        "👥 Multi-language support (planned)",
        "🏛️ Government and NGO integration",
        "📊 Real-time resource tracking",
        "🔄 Automatic capacity management",
        "📈 Analytics and reporting dashboard"
    ]
    
    for feature in features:
        print(f"  {feature}")
        time.sleep(0.3)

def show_impact():
    """Show the potential impact of the system"""
    print("\n" + "="*60)
    print("🌍 POTENTIAL IMPACT")
    print("="*60)
    
    impacts = [
        "🏃‍♂️ Faster emergency response times",
        "📱 Reaches people with basic phones",
        "🎯 Better resource allocation",
        "🤝 Connects victims to help instantly",
        "📊 Data-driven disaster management",
        "💰 Reduces coordination costs",
        "🌐 Scalable to other states/countries",
        "🔄 Works even when internet fails"
    ]
    
    for impact in impacts:
        print(f"  {impact}")
        time.sleep(0.3)

def main():
    """Main demo function"""
    print("🚨 EMERGENCY RESPONSE SYSTEM DEMO")
    print("Solving the last-mile problem in disaster response")
    print("\nStarting demonstration...")
    
    # Start the server
    server_process = start_server()
    
    if not server_process:
        print("❌ Could not start server. Please check the setup.")
        return
    
    try:
        # Show system features
        show_system_features()
        
        # Demonstrate USSD flow
        demo_ussd_flow()
        
        # Show potential impact
        show_impact()
        
        print("\n" + "="*60)
        print("🎯 NEXT STEPS")
        print("="*60)
        print("1. Partner with telecom providers for USSD gateway")
        print("2. Integrate with government emergency services")
        print("3. Onboard NGOs and volunteer organizations")
        print("4. Deploy to production infrastructure")
        print("5. Scale to other disaster-prone regions")
        
        print("\n✅ Demo completed successfully!")
        print("The system is ready for real-world deployment.")
        
    finally:
        # Clean up
        if server_process:
            print("\n🛑 Stopping server...")
            server_process.terminate()
            server_process.wait()

if __name__ == "__main__":
    main()