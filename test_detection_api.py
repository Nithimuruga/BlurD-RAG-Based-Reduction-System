#!/usr/bin/env python3

import requests
import json

def test_detection_endpoint():
    """Test the /detect/text endpoint"""
    url = "http://localhost:8000/detect/text"
    
    payload = {
        "text": "Hello John Smith, your email is john@example.com and phone is +1-555-123-4567. Your SSN is 123-45-6789."
    }
    
    try:
        print("Testing /detect/text endpoint...")
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API Response:")
            print(json.dumps(result, indent=2))
            
            # Check for detections
            if "detections" in result:
                print(f"\n🎯 Found {len(result['detections'])} detections:")
                for detection in result["detections"]:
                    print(f"- {detection['type']}: '{detection['text']}' (confidence: {detection['confidence']:.2f}) [{detection['source']}]")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        print("Testing health endpoint...")
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    print("=== API Testing ===\n")
    
    # Test health first
    if test_health_endpoint():
        print()
        # Test detection
        test_detection_endpoint()
    else:
        print("Server is not responding. Please check if it's running on port 8000.")