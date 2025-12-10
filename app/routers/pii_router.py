"""
Router for PII detection and redaction endpoints.
Provides APIs for PII detection, redaction, and compliance reporting.
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Any, Optional, Union
import os
import logging
import uuid
import json
from datetime import datetime
import tempfile
import shutil
from pathlib import Path

from app.schemas.pii_schemas import (
    PIIDetectionRequest, 
    PIIDetectionResult, 
    RedactionRequest,
    RedactionResult,
    ComplianceFramework,
    RedactionStrategy,
    PIITypeSelection,
    AuditLogEntry
)

from app.services.detection_orchestrator import DetectionOrchestrator
from app.services.redaction_service import RedactionService
from app.services.data_ingestion_service import DataIngestionService
from app.services.output_formatter import OutputFormatter
from app.services.text_preprocessing import TextPreprocessor

# Setup logging
logger = logging.getLogger(__name__)

# Create router
pii_router = APIRouter(
    prefix="/pii",
    tags=["PII Detection and Redaction"],
    responses={404: {"description": "Not found"}},
)

# Initialize services
detection_orchestrator = DetectionOrchestrator()
redaction_service = RedactionService()
data_ingestion_service = DataIngestionService()
output_formatter = OutputFormatter(output_dir="redacted_outputs")
text_preprocessor = TextPreprocessor()

# Helper functions
def get_temp_file_path(suffix: str = None) -> str:
    """Create a temporary file path with optional suffix"""
    temp_dir = os.path.join(os.getcwd(), "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    filename = f"{uuid.uuid4()}{suffix if suffix else ''}"
    return os.path.join(temp_dir, filename)

async def save_upload_file(upload_file: UploadFile) -> str:
    """Save an uploaded file and return the path"""
    # Get file extension
    file_extension = os.path.splitext(upload_file.filename)[1]
    temp_file_path = get_temp_file_path(file_extension)
    
    # Save uploaded file
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return temp_file_path

async def cleanup_temp_files(background_tasks: BackgroundTasks, file_paths: List[str]):
    """Schedule cleanup of temporary files"""
    def delete_files():
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info(f"Deleted temporary file: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting temporary file {file_path}: {e}")
    
    background_tasks.add_task(delete_files)

# API Endpoints
@pii_router.post("/detect", response_model=PIIDetectionResult)
async def detect_pii(
    background_tasks: BackgroundTasks,
    request: PIIDetectionRequest = None,
    file: UploadFile = File(None),
    text: str = Form(None),
    pii_types: List[str] = Query(None),
    compliance_frameworks: List[str] = Query(None)
):
    """
    Detect PII in text or uploaded file
    """
    temp_files = []
    
    try:
        # Handle form data or JSON request
        if request:
            input_text = request.text
            source_type = "request"
            pii_types = request.pii_types
            compliance_frameworks = request.compliance_frameworks
        elif file:
            temp_file_path = await save_upload_file(file)
            temp_files.append(temp_file_path)
            input_text = await data_ingestion_service.extract_text_from_file(temp_file_path)
            source_type = "file"
        elif text:
            input_text = text
            source_type = "form"
        else:
            raise HTTPException(status_code=400, detail="No input provided. Please provide text or upload a file.")
        
        # Preprocess text
        preprocessed_text = await text_preprocessor.preprocess_text(input_text)
        
        # Detect PII
        detection_result = await detection_orchestrator.detect_pii(
            preprocessed_text,
            pii_types=pii_types,
            compliance_frameworks=compliance_frameworks
        )
        
        # Schedule cleanup of temporary files
        if temp_files:
            await cleanup_temp_files(background_tasks, temp_files)
        
        # Return result
        return detection_result
        
    except Exception as e:
        logger.error(f"Error in PII detection: {e}")
        # Clean up temp files in case of error
        if temp_files:
            await cleanup_temp_files(background_tasks, temp_files)
        raise HTTPException(status_code=500, detail=f"Error detecting PII: {str(e)}")

@pii_router.post("/redact", response_model=RedactionResult)
async def redact_pii(
    background_tasks: BackgroundTasks,
    request: RedactionRequest = None,
    file: UploadFile = File(None),
    text: str = Form(None),
    pii_types: List[str] = Query(None),
    compliance_frameworks: List[str] = Query(None),
    redaction_strategy: str = Form("mask"),
    output_format: str = Form(None)
):
    """
    Detect and redact PII in text or uploaded file
    """
    temp_files = []
    
    try:
        # Handle form data or JSON request
        if request:
            input_text = request.text
            source_type = "request"
            pii_types = request.pii_types
            compliance_frameworks = request.compliance_frameworks
            redaction_strategy = request.redaction_strategy
            output_format = request.output_format
        elif file:
            temp_file_path = await save_upload_file(file)
            temp_files.append(temp_file_path)
            input_text = await data_ingestion_service.extract_text_from_file(temp_file_path)
            source_type = "file"
            original_filename = file.filename
        elif text:
            input_text = text
            source_type = "form"
            original_filename = None
        else:
            raise HTTPException(status_code=400, detail="No input provided. Please provide text or upload a file.")
        
        # Preprocess text
        preprocessed_text = await text_preprocessor.preprocess_text(input_text)
        
        # Detect PII
        detection_result = await detection_orchestrator.detect_pii(
            preprocessed_text,
            pii_types=pii_types,
            compliance_frameworks=compliance_frameworks
        )
        
        # Apply redaction
        redaction_result = await redaction_service.redact(
            input_text=preprocessed_text,
            detected_entities=detection_result.detected_entities,
            strategy=redaction_strategy
        )
        
        # Generate output in requested format
        if output_format:
            metadata = {
                "document_id": str(uuid.uuid4()),
                "original_file_name": original_filename,
                "original_file_path": temp_files[0] if temp_files else None,
                "compliance_frameworks": compliance_frameworks,
                "timestamp": datetime.now().isoformat()
            }
            
            output_result = await output_formatter.format_output(
                redaction_result=redaction_result,
                format_type=output_format,
                metadata=metadata
            )
            
            # Add output info to redaction result
            redaction_result.output_info = output_result
        
        # Schedule cleanup of temporary files
        if temp_files:
            await cleanup_temp_files(background_tasks, temp_files)
        
        # Return result
        return redaction_result
        
    except Exception as e:
        logger.error(f"Error in PII redaction: {e}")
        # Clean up temp files in case of error
        if temp_files:
            await cleanup_temp_files(background_tasks, temp_files)
        raise HTTPException(status_code=500, detail=f"Error redacting PII: {str(e)}")

@pii_router.post("/redact/download")
async def redact_and_download(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    pii_types: List[str] = Query(None),
    compliance_frameworks: List[str] = Query(None),
    redaction_strategy: str = Form("mask"),
    output_format: str = Form("pdf")
):
    """
    Detect and redact PII in uploaded file, then return the redacted file for download
    """
    temp_files = []
    
    try:
        # Save uploaded file
        temp_file_path = await save_upload_file(file)
        temp_files.append(temp_file_path)
        
        # Extract text
        input_text = await data_ingestion_service.extract_text_from_file(temp_file_path)
        
        # Preprocess text
        preprocessed_text = await text_preprocessor.preprocess_text(input_text)
        
        # Detect PII
        detection_result = await detection_orchestrator.detect_pii(
            preprocessed_text,
            pii_types=pii_types,
            compliance_frameworks=compliance_frameworks
        )
        
        # Apply redaction
        redaction_result = await redaction_service.redact(
            input_text=preprocessed_text,
            detected_entities=detection_result.detected_entities,
            strategy=redaction_strategy
        )
        
        # Generate output file
        filename_base = os.path.splitext(file.filename)[0]
        output_filename = f"redacted_{filename_base}.{output_format}"
        output_path = os.path.join("redacted_outputs", output_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        metadata = {
            "document_id": str(uuid.uuid4()),
            "original_file_name": file.filename,
            "original_file_path": temp_file_path,
            "compliance_frameworks": compliance_frameworks,
            "timestamp": datetime.now().isoformat()
        }
        
        output_result = await output_formatter.format_output(
            redaction_result=redaction_result,
            format_type=output_format,
            output_path=output_path,
            metadata=metadata
        )
        
        if not output_result["success"]:
            raise HTTPException(status_code=500, detail=f"Error creating output file: {output_result.get('error')}")
        
        # Schedule cleanup of temporary files (but not the output file)
        await cleanup_temp_files(background_tasks, temp_files)
        
        # Return file for download
        return FileResponse(
            path=output_path,
            filename=output_filename,
            media_type=f"application/{output_format}",
            background=background_tasks
        )
        
    except Exception as e:
        logger.error(f"Error in redact and download: {e}")
        # Clean up temp files in case of error
        if temp_files:
            await cleanup_temp_files(background_tasks, temp_files)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@pii_router.get("/compliance/check")
async def compliance_check(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    text: str = Form(None),
    compliance_frameworks: List[str] = Query(...)
):
    """
    Check if text or file complies with specified compliance frameworks
    """
    temp_files = []
    
    try:
        # Handle input
        if file:
            temp_file_path = await save_upload_file(file)
            temp_files.append(temp_file_path)
            input_text = await data_ingestion_service.extract_text_from_file(temp_file_path)
        elif text:
            input_text = text
        else:
            raise HTTPException(status_code=400, detail="No input provided. Please provide text or upload a file.")
        
        # Preprocess text
        preprocessed_text = await text_preprocessor.preprocess_text(input_text)
        
        # Detect PII for specified compliance frameworks
        detection_result = await detection_orchestrator.detect_pii(
            preprocessed_text,
            compliance_frameworks=compliance_frameworks
        )
        
        # Determine if compliant (no PII found)
        is_compliant = len(detection_result.detected_entities) == 0
        
        # Create compliance report
        compliance_report = {
            "is_compliant": is_compliant,
            "compliance_frameworks": compliance_frameworks,
            "pii_detected": not is_compliant,
            "detected_entity_count": len(detection_result.detected_entities),
            "pii_types_found": list(set([entity.pii_type for entity in detection_result.detected_entities])),
            "risk_level": "high" if not is_compliant else "low",
            "timestamp": datetime.now().isoformat()
        }
        
        # Schedule cleanup of temporary files
        if temp_files:
            await cleanup_temp_files(background_tasks, temp_files)
        
        # Return compliance report
        return compliance_report
        
    except Exception as e:
        logger.error(f"Error in compliance check: {e}")
        # Clean up temp files in case of error
        if temp_files:
            await cleanup_temp_files(background_tasks, temp_files)
        raise HTTPException(status_code=500, detail=f"Error checking compliance: {str(e)}")

@pii_router.post("/audit/log")
async def create_audit_log(audit_log: AuditLogEntry):
    """
    Create an audit log entry for a PII operation
    """
    try:
        # TODO: Store audit log in database or file
        # For now, just log and return
        logger.info(f"Audit log: {audit_log.dict()}")
        return {"success": True, "message": "Audit log created"}
    except Exception as e:
        logger.error(f"Error creating audit log: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating audit log: {str(e)}")

@pii_router.get("/audit/logs")
async def get_audit_logs(
    start_date: str = None,
    end_date: str = None,
    operation: str = None,
    user_id: str = None,
    limit: int = 100
):
    """
    Get audit logs with optional filters
    """
    try:
        # TODO: Retrieve audit logs from database or file
        # For now, return dummy data
        return {
            "success": True,
            "message": "This is a placeholder for audit log retrieval",
            "logs": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "operation": "redact_pdf",
                    "user_id": "user123",
                    "document_id": "doc456",
                    "success": True
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")