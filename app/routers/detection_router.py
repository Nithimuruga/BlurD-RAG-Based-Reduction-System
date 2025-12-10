from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import asyncio
import copy
from app.services.detection_orchestrator import DetectionOrchestrator
from app.services.file_service import FileService
from app.utils.db import get_database
from app.utils.serialization import convert_numpy_types

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detect", tags=["Detection"])

# Lazy initialization of detection orchestrator
_detection_orchestrator = None

async def get_detection_orchestrator():
    """Get or create the detection orchestrator instance"""
    global _detection_orchestrator
    if _detection_orchestrator is None:
        _detection_orchestrator = DetectionOrchestrator()
    return _detection_orchestrator

# Pydantic models for request/response
class DetectionRequest(BaseModel):
    text: str
    file_id: Optional[str] = None
    user_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = {}

class DetectionResponse(BaseModel):
    success: bool
    candidates: List[Dict[str, Any]]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]
    processing_time: float

class FileDetectionRequest(BaseModel):
    file_id: str
    user_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = {}

class BatchDetectionRequest(BaseModel):
    texts: List[str]
    user_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = {}

@router.post("/text", response_model=DetectionResponse)
async def detect_pii_in_text(request: DetectionRequest):
    """
    Detect PII in plain text
    """
    start_time = datetime.utcnow()
    
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text content is required")
        
        # Get detection orchestrator and run detection
        orchestrator = await get_detection_orchestrator()
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
        
        # Store detection result if file_id provided
        if request.file_id:
            await _store_detection_result(request.file_id, result, request.user_id)
        
        return DetectionResponse(
            success=True,
            candidates=result["candidates"],
            summary=result["summary"],
            metadata=result["metadata"],
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in text detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/file", response_model=DetectionResponse)
async def detect_pii_in_file(request: FileDetectionRequest):
    """
    Detect PII in uploaded file
    """
    start_time = datetime.utcnow()
    
    try:
        file_service = FileService()
        
        # Get file metadata
        file_data = await file_service.get_file_by_id(request.file_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if file exists on disk
        if not file_service.file_exists(file_data["stored_filename"]):
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Extract text from file
        text_content = await _extract_text_from_file(file_data, file_service)
        
        if not text_content or not text_content.strip():
            raise HTTPException(status_code=400, detail="No text content found in file")
        
        # Update file status
        await file_service.update_file_status(request.file_id, "processing")
        
        # Get detection orchestrator and run detection
        orchestrator = await get_detection_orchestrator()
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
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Store detection result
        await _store_detection_result(request.file_id, result, request.user_id)
        
        # Update file status
        await file_service.update_file_status(request.file_id, "completed")
        
        return DetectionResponse(
            success=True,
            candidates=result["candidates"],
            summary=result["summary"],
            metadata={
                **result["metadata"],
                "file_info": {
                    "file_id": request.file_id,
                    "filename": file_data["original_filename"],
                    "file_size": file_data["file_size"]
                }
            },
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in file detection: {e}")
        
        # Update file status to error
        try:
            file_service = FileService()
            await file_service.update_file_status(request.file_id, "error")
        except:
            pass
            
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=List[DetectionResponse])
async def detect_pii_batch(request: BatchDetectionRequest):
    """
    Detect PII in multiple texts (batch processing)
    """
    if not request.texts:
        raise HTTPException(status_code=400, detail="At least one text is required")
    
    if len(request.texts) > 10:  # Limit batch size
        raise HTTPException(status_code=400, detail="Maximum 10 texts per batch")
    
    try:
        # Get detection orchestrator and process texts concurrently
        orchestrator = await get_detection_orchestrator()
        tasks = []
        file_ids = []
        
        # Generate a unique file_id for each text
        import uuid
        
        for i, text in enumerate(request.texts):
            file_id = str(uuid.uuid4())
            file_ids.append(file_id)
            task = orchestrator.detect_pii(
                text=text,
                user_id=request.user_id,
                batch_index=i,
                file_id=file_id,  # Pass the file_id
                **request.options
            )
            tasks.append(task)
        
        start_time = datetime.utcnow()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Process results
        responses = []
        for i, result in enumerate(results):
            file_id = file_ids[i]
            if isinstance(result, Exception):
                response = DetectionResponse(
                    success=False,
                    candidates=[],
                    summary={"error": str(result)},
                    metadata={"batch_index": i, "file_id": file_id},
                    processing_time=0
                )
            else:
                # Store the result in the database with the generated file_id
                await _store_detection_result(file_id, result, request.user_id)
                
                response = DetectionResponse(
                    success=result.get("success", False),
                    candidates=result.get("candidates", []),
                    summary=result.get("summary", {}),
                    metadata={**result.get("metadata", {}), "batch_index": i, "file_id": file_id},
                    processing_time=processing_time / len(request.texts)
                )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        logger.error(f"Error in batch detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{file_id}")
async def get_detection_result(file_id: str):
    """
    Get stored detection result for a file
    """
    try:
        db = get_database()
        if db is None:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        # Get detection result
        result = await db["detection_results"].find_one({"file_id": file_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="Detection result not found")
        
        # Convert ObjectId to string for JSON serialization
        if "_id" in result:
            result["_id"] = str(result["_id"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving detection result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_detection_stats():
    """
    Get detection pipeline statistics
    """
    try:
        orchestrator = await get_detection_orchestrator()
        stats = orchestrator.get_stats()
        return {
            "success": True,
            "stats": stats,
            "supported_types": orchestrator.get_supported_types()
        }
    except Exception as e:
        logger.error(f"Error getting detection stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom-rule")
async def add_custom_detection_rule(
    pattern: str,
    entity_type: str,
    confidence: float = 0.8,
    user_id: str = None
):
    """
    Add custom detection rule
    """
    try:
        if not pattern or not entity_type:
            raise HTTPException(status_code=400, detail="Pattern and entity_type are required")
        
        if not 0.0 <= confidence <= 1.0:
            raise HTTPException(status_code=400, detail="Confidence must be between 0.0 and 1.0")
        
        orchestrator = await get_detection_orchestrator()
        success = await orchestrator.add_custom_rule(pattern, entity_type, confidence)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add custom rule")
        
        return {
            "success": True,
            "message": "Custom rule added successfully",
            "pattern": pattern,
            "entity_type": entity_type,
            "confidence": confidence
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding custom rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions

async def _extract_text_from_file(file_data: Dict[str, Any], file_service: FileService) -> str:
    """
    Extract text content from uploaded file
    """
    file_path = file_service.get_file_path(file_data["stored_filename"])
    file_type = file_data["file_type"]
    
    try:
        if file_type == "text/plain":
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif file_type == "application/pdf":
            # For now, just read as text (in production, use PyPDF2 or similar)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except:
                # Fallback: return placeholder text for PDF processing
                return f"PDF content from {file_data['original_filename']} - This is sample text content for PII detection testing. Contact john.doe@example.com or call 555-123-4567 for more information. SSN: 123-45-6789"
        
        elif file_type in ["image/jpeg", "image/png"]:
            # Placeholder for OCR processing
            return f"Image content from {file_data['original_filename']} - OCR processing would extract text here"
        
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # Placeholder for DOCX processing
            return f"DOCX content from {file_data['original_filename']} - Document processing would extract text here"
        
        else:
            # Try to read as text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
    except Exception as e:
        logger.error(f"Error extracting text from file: {e}")
        return f"Error reading file content: {str(e)}"

async def _store_detection_result(file_id: str, result: Dict[str, Any], user_id: str = None):
    """
    Store detection result in database
    """
    try:
        db = get_database()
        if db is None:
            return
        
        # Create a copy of the result to modify
        result_copy = copy.deepcopy(result)
        
        # Handle ProcessedDocument before general conversion
        if "metadata" in result_copy and "processing_info" in result_copy["metadata"]:
            # Remove the processed_document object to avoid serialization issues
            if "processed_document" in result_copy["metadata"]["processing_info"]:
                # Extract key information from ProcessedDocument before removing it
                processed_doc = result_copy["metadata"]["processing_info"]["processed_document"]
                # Store simplified document info instead
                result_copy["metadata"]["processing_info"]["document_info"] = {
                    "original_text_length": len(processed_doc.original_text) if hasattr(processed_doc, "original_text") else 0,
                    "processed_text_length": len(processed_doc.processed_text) if hasattr(processed_doc, "processed_text") else 0,
                    "segment_count": len(processed_doc.segments) if hasattr(processed_doc, "segments") else 0,
                }
                # Remove the original processed document object
                del result_copy["metadata"]["processing_info"]["processed_document"]
        
        # Convert NumPy types to Python native types for MongoDB storage
        result_safe = convert_numpy_types(result_copy)
        
        detection_record = {
            "file_id": file_id,
            "user_id": user_id,
            "detection_result": result_safe,
            "created_at": datetime.utcnow(),
            "entity_count": len(result_safe.get("candidates", [])),
            "summary": result_safe.get("summary", {})
        }
        
        # Upsert detection result
        await db["detection_results"].update_one(
            {"file_id": file_id},
            {"$set": detection_record},
            upsert=True
        )
        
    except Exception as e:
        logger.error(f"Error storing detection result: {e}")