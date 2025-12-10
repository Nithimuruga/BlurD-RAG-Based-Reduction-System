#!/usr/bin/env python3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Simple FastAPI app for testing
app = FastAPI(title="Simple PII Detection API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DetectionRequest(BaseModel):
    text: str

class DetectionResponse(BaseModel):
    text: str
    detections: list
    message: str

@app.get("/")
def read_root():
    return {"message": "Simple PII Detection API", "status": "running"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "API is running"
    }

@app.post("/detect/text")
def detect_pii_simple(request: DetectionRequest):
    """Simple PII detection (mock for testing)"""
    text = request.text
    
    # Simple mock detections for testing
    detections = []
    
    # Basic email detection
    if "@" in text and "." in text:
        detections.append({
            "type": "EMAIL",
            "text": "email@example.com",
            "confidence": 0.9,
            "source": "simple_regex"
        })
    
    # Basic phone detection
    if any(char in text for char in ["555", "123", "+"]):
        detections.append({
            "type": "PHONE",
            "text": "phone_number",
            "confidence": 0.85,
            "source": "simple_regex"
        })
    
    return DetectionResponse(
        text=text,
        detections=detections,
        message=f"Processed text with {len(detections)} simple detections"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)