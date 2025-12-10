"""
Quick test script for PII detection pipeline
Usage: python quick_test.py
"""

import requests
import json

def quick_test():
    """Quick test of the PII detection API"""
    
    # Test text with various PII types
    test_text = """
    John Smith's email is john.smith@company.com
    His phone number is (555) 123-4567
    SSN: 123-45-6789
    Credit Card: 4532 1234 5678 9012
    He works at Acme Corporation in New York.
    """
    
    try:
        # Test the detection endpoint
        response = requests.post(
            "http://127.0.0.1:8000/detect/text",
            json={
                "text": test_text,
                "user_id": "quick_test_user"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ PII Detection API is working!")
            print(f"Found {result['summary']['total_entities']} entities:")
            
            for candidate in result.get('candidates', []):
                print(f"  - {candidate['type']}: '{candidate['text']}' "
                      f"(confidence: {candidate['confidence']:.2f})")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the server is running:")
        print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    quick_test()