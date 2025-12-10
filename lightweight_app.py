"""
Lightweight FastAPI app that delays ML model loading
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from app.utils.db import connect_to_mongo, close_mongo_connection
from app.routers import upload_router, example_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Lightweight PII Detection API", version="1.0.0")

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

# Include routers
app.include_router(upload_router.router)
app.include_router(example_router.router)

# Pydantic models
class DetectionRequest(BaseModel):
    text: str
    file_id: Optional[str] = None
    user_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = {}

class FileDetectionRequest(BaseModel):
    file_id: str
    user_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = {}

# Global variable to track if models are initialized
_models_loaded = False

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    logger.info("Database connected, skipping ML model initialization for faster startup")

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

@app.get("/")
def read_root():
    return {"message": "Lightweight PII Detection API ready!", "models_loaded": _models_loaded}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "API is running",
        "models_loaded": _models_loaded
    }

async def _get_orchestrator():
    """Lazy load the detection orchestrator when first needed"""
    global _models_loaded
    try:
        from app.services.detection_orchestrator import PiiDetectionOrchestrator
        
        if not _models_loaded:
            logger.info("Loading ML models on first use...")
        
        orchestrator = PiiDetectionOrchestrator()
        await orchestrator.initialize()
        _models_loaded = True
        return orchestrator
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        raise HTTPException(status_code=500, detail=f"Model initialization failed: {str(e)}")

@app.post("/detect/text")
async def detect_pii_in_text(request: DetectionRequest):
    """Detect PII in text with lazy model loading"""
    start_time = datetime.utcnow()
    
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text content is required")
        
        logger.info(f"Processing text detection request for user: {request.user_id}")
        
        # Lazy load orchestrator (this will download models if needed)
        orchestrator = await _get_orchestrator()
        
        # Run detection
        result = await orchestrator.detect_pii(
            text=request.text,
            user_id=request.user_id,
            **request.options
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=f"Detection failed: {result.get('error', 'Unknown error')}"
            )
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        result["processing_time"] = processing_time
        
        logger.info(f"Text detection completed in {processing_time:.2f}s, found {result.get('summary', {}).get('total_entities', 0)} entities")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in text detection: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/detect/file")
async def detect_pii_in_file(request: FileDetectionRequest):
    """Detect PII in uploaded file with lazy model loading"""
    start_time = datetime.utcnow()
    
    try:
        if not request.file_id:
            raise HTTPException(status_code=400, detail="File ID is required")
        
        logger.info(f"Processing file detection request for file: {request.file_id}")
        
        # Import file service
        from app.services.file_service import FileService
        
        # Get file service and retrieve file data
        file_service = FileService()
        file_data = await file_service.get_file_by_id(request.file_id)
        
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Extract text from file
        text_content = await _extract_text_from_file(file_data, file_service)
        
        if not text_content or not text_content.strip():
            raise HTTPException(status_code=400, detail="No text content found in file")
        
        # Update file status
        await file_service.update_file_status(request.file_id, "processing")
        
        # Lazy load orchestrator and run detection
        orchestrator = await _get_orchestrator()
        
        result = await orchestrator.detect_pii(
            text=text_content,
            user_id=request.user_id,
            file_id=request.file_id,
            file_path=file_data["file_path"],
            original_filename=file_data["original_filename"],
            **request.options
        )
        
        if not result.get("success", False):
            await file_service.update_file_status(request.file_id, "error")
            raise HTTPException(
                status_code=500,
                detail=f"Detection failed: {result.get('error', 'Unknown error')}"
            )
        
        # Update file status to completed
        await file_service.update_file_status(request.file_id, "completed")
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        result["processing_time"] = processing_time
        
        logger.info(f"File detection completed in {processing_time:.2f}s, found {result.get('summary', {}).get('total_entities', 0)} entities")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in file detection: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def _extract_text_from_file(file_data: dict, file_service) -> str:
    """Extract text content from file based on file type"""
    try:
        file_path = file_data["file_path"]
        file_type = file_data.get("content_type", "").lower()
        
        if file_type == "text/plain" or file_path.endswith('.txt'):
            return await file_service.extract_text_from_txt(file_path)
        elif file_type == "application/pdf" or file_path.endswith('.pdf'):
            return await file_service.extract_text_from_pdf(file_path)
        elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"] or file_path.endswith('.docx'):
            return await file_service.extract_text_from_docx(file_path)
        else:
            # Try to read as plain text
            return await file_service.extract_text_from_txt(file_path)
            
    except Exception as e:
        logger.error(f"Error extracting text from file: {e}")
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Lightweight PII Detection API...")
    uvicorn.run(app, host="127.0.0.1", port=8000)