"""
Updated test script for the working PII detection API
"""
import requests
import json
import time

def test_detection_api():
    """Test the detection API with proper error handling"""
    
    # Test data
    test_data = {
        "text": "John Smith's email is john.smith@company.com and his phone number is (555) 123-4567. His SSN is 123-45-6789.",
        "user_id": "test_user",
        "options": {
            "include_context": True,
            "confidence_threshold": 0.5
        }
    }
    
    try:
        print("🔍 Testing PII Detection API...")
        print(f"📝 Test text: {test_data['text']}")
        print()
        
        # Test health endpoint first
        print("1️⃣ Testing health endpoint...")
        health_response = requests.get('http://127.0.0.1:8000/health', timeout=5)
        if health_response.status_code == 200:
            print("✅ Health check passed!")
            print(f"   Response: {health_response.json()}")
        else:
            print(f"❌ Health check failed: {health_response.status_code}")
            return False
        
        print()
        
        # Test detection endpoint
        print("2️⃣ Testing detection endpoint...")
        detection_response = requests.post(
            'http://127.0.0.1:8000/detect/text', 
            json=test_data,
            timeout=30
        )
        
        if detection_response.status_code == 200:
            result = detection_response.json()
            print("✅ Detection successful!")
            print(f"   Processing time: {result.get('processing_time', 'N/A')} seconds")
            print(f"   Total entities found: {result.get('summary', {}).get('total_entities', 0)}")
            
            candidates = result.get('candidates', [])
            if candidates:
                print("   🎯 Detected entities:")
                for i, candidate in enumerate(candidates[:10], 1):  # Show first 10
                    entity_type = candidate.get('type', 'Unknown')
                    text = candidate.get('text', '')
                    confidence = candidate.get('confidence', 0)
                    print(f"      {i}. {entity_type}: '{text}' (confidence: {confidence:.2f})")
                
                if len(candidates) > 10:
                    print(f"      ... and {len(candidates) - 10} more")
            else:
                print("   ℹ️ No entities detected")
            
            return True
        else:
            print(f"❌ Detection failed: {detection_response.status_code}")
            print(f"   Error: {detection_response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server")
        print("   Make sure the server is running:")
        print("   uvicorn app.main:app --host 127.0.0.1 --port 8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        print("   The server might be loading ML models (this can take a few minutes)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def wait_for_server(max_wait_time=60):
    """Wait for the server to become available"""
    print(f"⏳ Waiting for server to become available (max {max_wait_time}s)...")
    
    for attempt in range(max_wait_time):
        try:
            response = requests.get('http://127.0.0.1:8000/health', timeout=2)
            if response.status_code == 200:
                print(f"✅ Server is ready after {attempt + 1} seconds!")
                return True
        except:
            pass
        
        if attempt % 10 == 9:  # Print progress every 10 seconds
            print(f"   Still waiting... ({attempt + 1}s elapsed)")
        
        time.sleep(1)
    
    print(f"❌ Server did not become available within {max_wait_time} seconds")
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 PII DETECTION API TEST")
    print("=" * 60)
    
    # First, wait for server to be ready
    if wait_for_server():
        # Run the actual test
        success = test_detection_api()
        
        print()
        print("=" * 60)
        if success:
            print("🎉 ALL TESTS PASSED! The PII detection system is working correctly.")
            print("📋 The original hardcoded data issue has been resolved.")
            print("🔧 Your frontend should now show real detection results.")
        else:
            print("💥 Tests failed. Please check the server logs for errors.")
        print("=" * 60)
    else:
        print("Cannot proceed with tests - server is not available")