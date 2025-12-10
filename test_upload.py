"""
Test script for the FastAPI upload endpoint
Usage: python test_upload.py
"""

import requests
import json
from pathlib import Path

# Test file upload
def test_upload():
    url = "http://localhost:8000/upload/"
    
    # Create a simple test file
    test_file_path = Path("test_document.txt")
    test_file_path.write_text("This is a test document for upload.")
    
    try:
        # Prepare the request
        files = {"file": ("test_document.txt", open(test_file_path, "rb"), "text/plain")}
        data = {"user_id": "user123"}
        
        # Make the request
        response = requests.post(url, files=files, data=data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            file_id = response.json()["file_id"]
            print(f"\nFile uploaded successfully! File ID: {file_id}")
            
            # Test getting file metadata
            metadata_url = f"http://localhost:8000/upload/file/{file_id}"
            metadata_response = requests.get(metadata_url)
            print(f"\nFile Metadata: {json.dumps(metadata_response.json(), indent=2, default=str)}")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to FastAPI server.")
        print("Make sure the server is running with: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup test file
        if test_file_path.exists():
            test_file_path.unlink()

if __name__ == "__main__":
    test_upload()