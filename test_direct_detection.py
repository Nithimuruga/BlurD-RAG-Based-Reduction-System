"""
Direct test of the detection pipeline without FastAPI
"""
import asyncio
from app.services.detection_orchestrator import PiiDetectionOrchestrator

async def test_detection_directly():
    """Test detection directly without FastAPI"""
    print("Initializing detection orchestrator...")
    
    try:
        orchestrator = PiiDetectionOrchestrator()
        print("✅ Detection orchestrator initialized successfully")
        
        test_text = "John Smith's email is john.smith@company.com and his phone is (555) 123-4567"
        
        print(f"Testing detection on: {test_text}")
        
        result = await orchestrator.detect_pii(
            text=test_text,
            user_id="direct_test"
        )
        
        print("✅ Detection completed successfully")
        print(f"Found {result['summary']['total_entities']} entities:")
        
        for candidate in result.get('candidates', []):
            print(f"  - {candidate['type']}: '{candidate['text']}' (confidence: {candidate['confidence']:.2f})")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_detection_directly())
    if success:
        print("🎉 Direct detection test passed!")
    else:
        print("💥 Direct detection test failed!")