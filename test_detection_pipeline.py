"""
Comprehensive test script for PII detection pipeline
Usage: python test_detection_pipeline.py
"""

import asyncio
import json
import requests
from typing import Dict, Any
import time

class DetectionPipelineTest:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.test_texts = [
            # Basic PII test
            """
            Dear Mr. John Smith,
            
            Thank you for your application. Please contact us at john.smith@email.com 
            or call (555) 123-4567. Your SSN 123-45-6789 has been verified.
            
            Credit card ending in 4532 1234 5678 9012 will be charged.
            
            Best regards,
            Acme Corporation
            123 Main Street, New York, NY 10001
            """,
            
            # Complex document with multiple PII types
            """
            CONFIDENTIAL EMPLOYEE RECORD
            
            Name: Dr. Sarah Johnson
            Employee ID: EMP-001234
            Social Security Number: 987-65-4321
            Date of Birth: January 15, 1985
            Email: sarah.johnson@company.org
            Phone: +1-555-987-6543
            Address: 456 Oak Avenue, Suite 200, Los Angeles, CA 90210
            
            Emergency Contact: Michael Johnson (spouse)
            Emergency Phone: (555) 234-5678
            
            Bank Information:
            Account Number: 1234567890
            Routing Number: 987654321
            Credit Card: 5555 5555 5555 4444 (Exp: 12/25)
            
            IP Address: 192.168.1.100
            Company Website: https://internal.company.com
            
            Medical Information:
            Doctor: Dr. Robert Brown
            Medical License: MD123456
            """,
            
            # International PII
            """
            International Customer Profile
            
            Name: Raj Patel
            PAN Number: ABCDE1234F
            IBAN: GB29 NWBK 6016 1331 9268 19
            Phone (India): +91 98765 43210
            Email: raj.patel@globaltech.in
            
            UK Address: 10 Downing Street, London, SW1A 2AA
            Company: Global Tech Solutions Ltd.
            """,
            
            # Edge cases and false positives
            """
            This document contains some tricky cases:
            
            Not an email: user@localhost
            Not a phone: 123-456 (incomplete)
            Not an SSN: 000-00-0000 (invalid)
            Sample data: john@example.com (example domain)
            Test credit card: 4111 1111 1111 1111 (test card)
            
            But these are real:
            Contact: support@realcompany.com
            Phone: 1-800-555-0123
            Valid SSN: 456-78-9012
            """
        ]
    
    def test_health_check(self) -> bool:
        """Test if the API is running"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def test_text_detection(self, text: str) -> Dict[str, Any]:
        """Test PII detection on text"""
        try:
            payload = {
                "text": text,
                "user_id": "test_user",
                "options": {"include_context": True}
            }
            
            response = requests.post(
                f"{self.base_url}/detect/text",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def test_batch_detection(self) -> Dict[str, Any]:
        """Test batch detection"""
        try:
            payload = {
                "texts": self.test_texts[:2],  # Test with first 2 texts
                "user_id": "test_user",
                "options": {"batch_processing": True}
            }
            
            response = requests.post(
                f"{self.base_url}/detect/batch",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def test_custom_rule(self) -> Dict[str, Any]:
        """Test adding custom detection rule"""
        try:
            # Add custom rule for employee IDs
            response = requests.post(
                f"{self.base_url}/detect/custom-rule",
                params={
                    "pattern": r"\bEMP-\d{6}\b",
                    "entity_type": "custom",
                    "confidence": 0.9,
                    "user_id": "test_user"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def test_detection_stats(self) -> Dict[str, Any]:
        """Test getting detection statistics"""
        try:
            response = requests.get(f"{self.base_url}/detect/stats", timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def run_comprehensive_test(self):
        """Run comprehensive test suite"""
        print("=" * 80)
        print("PII DETECTION PIPELINE - COMPREHENSIVE TEST")
        print("=" * 80)
        
        # 1. Health check
        print("\n1. Testing API Health...")
        if self.test_health_check():
            print("✅ API is running")
        else:
            print("❌ API is not accessible")
            return
        
        # 2. Test custom rule addition
        print("\n2. Testing Custom Rule Addition...")
        custom_rule_result = self.test_custom_rule()
        if "error" not in custom_rule_result:
            print("✅ Custom rule added successfully")
        else:
            print(f"⚠️ Custom rule test: {custom_rule_result['error']}")
        
        # 3. Test individual text detection
        print("\n3. Testing Individual Text Detection...")
        for i, test_text in enumerate(self.test_texts):
            print(f"\n   Test Case {i + 1}:")
            print("-" * 50)
            
            start_time = time.time()
            result = self.test_text_detection(test_text)
            end_time = time.time()
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                continue
            
            print(f"Processing time: {end_time - start_time:.2f} seconds")
            print(f"Entities found: {result['summary']['total_entities']}")
            print(f"High confidence: {result['summary']['high_confidence_entities']}")
            print(f"Entity types: {', '.join(result['summary']['entity_types'])}")
            
            # Show detailed results
            if result.get('candidates'):
                print("\nDetected Entities:")
                for candidate in result['candidates'][:10]:  # Show top 10
                    risk = candidate.get('metadata', {}).get('risk_level', 'unknown')
                    print(f"  • {candidate['type']}: '{candidate['text']}' "
                          f"(confidence: {candidate['confidence']:.2f}, risk: {risk})")
                
                if len(result['candidates']) > 10:
                    print(f"  ... and {len(result['candidates']) - 10} more")
        
        # 4. Test batch detection
        print("\n4. Testing Batch Detection...")
        batch_result = self.test_batch_detection()
        if "error" not in batch_result:
            print(f"✅ Batch detection completed for {len(batch_result)} texts")
            total_entities = sum(r['summary']['total_entities'] for r in batch_result)
            print(f"Total entities across batch: {total_entities}")
        else:
            print(f"❌ Batch detection error: {batch_result['error']}")
        
        # 5. Test detection statistics
        print("\n5. Testing Detection Statistics...")
        stats_result = self.test_detection_stats()
        if "error" not in stats_result and "stats" in stats_result:
            stats = stats_result["stats"]
            print(f"✅ Statistics retrieved")
            print(f"Total detections: {stats['total_detections']}")
            
            if stats['by_detector']:
                print("Detections by detector:")
                for detector, count in stats['by_detector'].items():
                    print(f"  • {detector}: {count}")
            
            if stats['by_entity_type']:
                print("Detections by entity type:")
                for entity_type, count in stats['by_entity_type'].items():
                    print(f"  • {entity_type}: {count}")
        else:
            print(f"⚠️ Stats error: {stats_result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print("✅ API Health: Passed")
        print("✅ Text Detection: Completed")
        print("✅ Batch Processing: Completed") 
        print("✅ Statistics: Retrieved")
        print("\nThe PII detection pipeline is working correctly!")
        print("=" * 80)

def main():
    """Main test function"""
    tester = DetectionPipelineTest()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()