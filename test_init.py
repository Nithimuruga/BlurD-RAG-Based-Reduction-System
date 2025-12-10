"""
Test detection orchestrator initialization
"""
import asyncio
from app.services.detection_orchestrator import PiiDetectionOrchestrator

async def test_initialization():
    print("Testing detection orchestrator initialization...")
    try:
        orch = PiiDetectionOrchestrator()
        print("✓ Orchestrator created")
        
        await orch.initialize()
        print("✓ Orchestrator initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_initialization())
    print(f"Result: {'Success' if success else 'Failed'}")