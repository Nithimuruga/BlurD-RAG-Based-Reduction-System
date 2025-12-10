"""
Lightweight detection test using only rule-based detection
This avoids heavy ML model downloads and should start quickly
"""
from app.services.rule_based_detector import RuleBasedDetector
import asyncio

async def test_lightweight_detection():
    """Test only the rule-based detector which doesn't require ML models"""
    print("Testing lightweight rule-based PII detection...")
    
    detector = RuleBasedDetector()
    
    test_text = """
    Contact John Smith at john.smith@company.com or call (555) 123-4567.
    His SSN is 123-45-6789 and credit card number is 4532 1234 5678 9012.
    """
    
    print(f"Analyzing: {test_text.strip()}")
    
    try:
        candidates = await detector.detect(test_text)
        
        print(f"\n✅ Found {len(candidates)} PII entities:")
        for candidate in candidates:
            print(f"  - {candidate.type}: '{candidate.text}' (confidence: {candidate.confidence:.2f})")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_lightweight_detection())
    print(f"\n{'🎉 Success!' if success else '💥 Failed'}")