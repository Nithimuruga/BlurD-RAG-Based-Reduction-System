"""
Simple test to verify the FastAPI server is running and accessible
"""
import requests
import json
from pathlib import Path
import time

def test_server_health():
    """Test if the server is running"""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"✅ Server is running! Status: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running or not accessible")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_upload_endpoint():
    """Test the upload endpoint with a simple file"""
    # Create a test file
    test_file = Path("test.txt")
    test_file.write_text("This is a test file for upload API testing.")
    
    try:
        url = "http://localhost:8000/upload/"
        
        # Prepare the multipart form data
        with open(test_file, 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            data = {'user_id': 'test_user_123'}
            
            response = requests.post(url, files=files, data=data, timeout=10)
        
        print(f"Upload Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful!")
            print(f"File ID: {result.get('file_id')}")
            print(f"Message: {result.get('message')}")
            return result.get('file_id')
        else:
            print(f"❌ Upload failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload test error: {e}")
        return None
    finally:
        # Cleanup test file
        if test_file.exists():
            test_file.unlink()

def test_get_metadata(file_id):
    """Test getting file metadata"""
    try:
        url = f"http://localhost:8000/upload/file/{file_id}"
        response = requests.get(url, timeout=5)
        
        print(f"Metadata Status Code: {response.status_code}")
        
        if response.status_code == 200:
            metadata = response.json()
            print("✅ Metadata retrieval successful!")
            print(json.dumps(metadata, indent=2, default=str))
        else:
            print(f"❌ Metadata retrieval failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Metadata test error: {e}")

def main():
    print("=== FastAPI Upload API Test ===\n")
    
    # Test 1: Check if server is running
    print("1. Testing server health...")
    if not test_server_health():
        print("\nPlease start the server first:")
        print("python start_server.py")
        return
    
    print()
    
    # Test 2: Test upload endpoint
    print("2. Testing file upload...")
    file_id = test_upload_endpoint()
    
    if file_id:
        print()
        # Test 3: Test metadata retrieval
        print("3. Testing metadata retrieval...")
        test_get_metadata(file_id)
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()