"""
FastAPI server without ML models to test basic functionality
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.utils.db import connect_to_mongo, close_mongo_connection
from app.routers import upload_router, example_router
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Test PII Detection API", version="1.0.0")

# CORS
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

# Include basic routers
app.include_router(upload_router.router)
app.include_router(example_router.router)

class DetectionRequest(BaseModel):
    text: str
    user_id: Optional[str] = None

@app.on_event("startup")
async def startup_db_client():
    logger.info("Starting up...")
    await connect_to_mongo()
    logger.info("Startup complete")

@app.on_event("shutdown")
async def shutdown_db_client():
    logger.info("Shutting down...")
    await close_mongo_connection()

@app.get("/")
def read_root():
    return {"message": "Test API is running!", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "Test API is running"
    }

@app.post("/detect/text")
async def detect_pii_simple(request: DetectionRequest):
    """Simple detection endpoint without ML models"""
    logger.info(f"Detection request from user: {request.user_id}")
    
    # Simple rule-based detection for testing
    text = request.text.lower()
    candidates = []
    
    # Simple email detection
    if "@" in text and "." in text:
        candidates.append({
            "id": "test_1",
            "type": "email", 
            "text": "detected email pattern",
            "confidence": 0.8,
            "start": 0,
            "end": len(request.text)
        })
    
    # Simple phone detection  
    if any(char.isdigit() for char in text) and ("(" in text or "-" in text):
        candidates.append({
            "id": "test_2",
            "type": "phone",
            "text": "detected phone pattern", 
            "confidence": 0.7,
            "start": 0,
            "end": len(request.text)
        })
    
    return {
        "success": True,
        "candidates": candidates,
        "summary": {
            "total_entities": len(candidates),
            "entity_types": [c["type"] for c in candidates]
        },
        "processing_time": 0.1
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Test PII Detection API...")
    uvicorn.run(app, host="127.0.0.1", port=8000)