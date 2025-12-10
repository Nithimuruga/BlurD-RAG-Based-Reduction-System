"""
Working FastAPI application with minimal detection capabilities for testing
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple detection logic without heavy ML models
class SimpleDetector:
    def __init__(self):
        self.patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b',
            "ssn": r'\b\d{3}-?\d{2}-?\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        }
    
    def detect(self, text: str) -> List[Dict[str, Any]]:
        candidates = []
        for entity_type, pattern in self.patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                candidates.append({
                    "id": f"{entity_type}_{len(candidates)}",
                    "type": entity_type,
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9,
                    "metadata": {}
                })
        return candidates

# Global detector instance
detector = SimpleDetector()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    yield
    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(
    title="Working PII Detection API",
    description="Simplified PII detection for testing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class DetectionRequest(BaseModel):
    text: str
    user_id: Optional[str] = "anonymous"
    options: Optional[Dict[str, Any]] = {}

class FileDetectionRequest(BaseModel):
    file_id: str
    user_id: Optional[str] = "anonymous"
    options: Optional[Dict[str, Any]] = {}

@app.get("/")
def root():
    return {
        "message": "Working PII Detection API",
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "message": "API is running correctly"
    }

@app.post("/detect/text")
async def detect_pii_text(request: DetectionRequest):
    """Detect PII in text using simple pattern matching"""
    try:
        logger.info(f"Processing text detection for user: {request.user_id}")
        
        candidates = detector.detect(request.text)
        
        return {
            "success": True,
            "candidates": candidates,
            "summary": {
                "total_entities": len(candidates),
                "entity_types": list(set(c["type"] for c in candidates)),
                "high_confidence_entities": len([c for c in candidates if c["confidence"] >= 0.8])
            },
            "processing_time": 0.05,
            "metadata": {
                "detector": "simple_regex",
                "text_length": len(request.text)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in text detection: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

@app.post("/detect/file")
async def detect_pii_file(request: FileDetectionRequest):
    """Placeholder for file detection - returns mock data for testing"""
    try:
        logger.info(f"Processing file detection for file: {request.file_id}")
        
        # Mock detection results for testing
        mock_candidates = [
            {
                "id": "mock_1",
                "type": "email",
                "text": "example@email.com",
                "start": 0,
                "end": 17,
                "confidence": 0.95,
                "metadata": {"source": "mock_file"}
            },
            {
                "id": "mock_2", 
                "type": "phone",
                "text": "(555) 123-4567",
                "start": 20,
                "end": 34,
                "confidence": 0.90,
                "metadata": {"source": "mock_file"}
            }
        ]
        
        return {
            "success": True,
            "candidates": mock_candidates,
            "summary": {
                "total_entities": len(mock_candidates),
                "entity_types": ["email", "phone"],
                "high_confidence_entities": 2
            },
            "processing_time": 0.1,
            "metadata": {
                "file_id": request.file_id,
                "detector": "mock_for_testing"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in file detection: {e}")
        raise HTTPException(status_code=500, detail=f"File detection failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Working PII Detection API...")
    uvicorn.run(app, host="127.0.0.1", port=8000)