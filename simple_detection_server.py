"""
Simple FastAPI server with rule-based PII detection only
This avoids heavy ML model downloads for quick testing
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.rule_based_detector import RuleBasedDetector
import asyncio

app = FastAPI(title="Simple PII Detection API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global detector instance
detector = RuleBasedDetector()

class DetectionRequest(BaseModel):
    text: str
    user_id: str = "anonymous"

class DetectionResponse(BaseModel):
    success: bool
    entities_found: int
    candidates: List[Dict[str, Any]]
    processing_time: float

@app.get("/")
def root():
    return {"message": "Simple PII Detection API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy", "detector": "rule-based"}

@app.post("/detect/text", response_model=DetectionResponse)
async def detect_pii_text(request: DetectionRequest):
    """Detect PII in text using rule-based patterns only"""
    try:
        import time
        start_time = time.time()
        
        candidates = await detector.detect(request.text)
        
        processing_time = time.time() - start_time
        
        # Convert candidates to dict format
        candidates_dict = []
        for candidate in candidates:
            candidates_dict.append({
                "id": f"candidate_{len(candidates_dict)}",
                "type": str(candidate.type),
                "text": candidate.text,
                "start": candidate.start,
                "end": candidate.end,
                "confidence": candidate.confidence,
                "metadata": candidate.metadata or {}
            })
        
        return DetectionResponse(
            success=True,
            entities_found=len(candidates_dict),
            candidates=candidates_dict,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Simple PII Detection API...")
    uvicorn.run(app, host="127.0.0.1", port=8002)