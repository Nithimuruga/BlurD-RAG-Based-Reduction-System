from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from uuid import uuid4
import os
from datetime import datetime
from app.utils.db import get_database
from app.models.file_model import FileModel
from app.schemas.upload_schemas import FileUploadResponse
import aiofiles
from pathlib import Path

router = APIRouter(prefix="/upload", tags=["Upload"])

# Create upload directory
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types with their MIME types and extensions
ALLOWED_TYPES = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"]
}

# Maximum file size (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

@router.post("/", response_model=FileUploadResponse)
async def upload_file(
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload a file and store its metadata in MongoDB.
    
    Accepts: PDF, DOCX, XLSX, JPG, PNG files
    Returns: file_id for tracking the uploaded file
    """
    
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        allowed_formats = ", ".join([ext for exts in ALLOWED_TYPES.values() for ext in exts])
        raise HTTPException(
            status_code=400, 
            detail=f"File type '{file.content_type}' not allowed. Allowed formats: {allowed_formats}"
        )
    
    # Validate file extension matches content type
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_TYPES.get(file.content_type, []):
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{file_ext}' doesn't match content type '{file.content_type}'"
        )
    
    # Read file content to check size
    content = await file.read()
    file_size = len(content)
    
    # Validate file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file not allowed")
    
    # Generate unique file ID and create stored filename
    file_id = str(uuid4())
    stored_filename = f"{file_id}{file_ext}"
    file_path = UPLOAD_DIR / stored_filename
    
    try:
        # Save file asynchronously
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        
        # Create file metadata
        file_model = FileModel(
            user_id=user_id,
            file_id=file_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_type=file.content_type,
            file_size=file_size,
            status="uploaded",
            upload_time=datetime.utcnow(),
            file_path=str(file_path)
        )
        
        # Store metadata in MongoDB
        db = get_database()
        if db is None:
            # For demo purposes, just log the metadata when DB is unavailable
            print("Warning: MongoDB not available. File metadata:")
            print(file_model.to_dict())
        else:
            await db["files"].insert_one(file_model.to_dict())
        
        return FileUploadResponse(
            file_id=file_id,
            message="File uploaded successfully",
            filename=file.filename,
            file_size=file_size
        )
        
    except Exception as e:
        # Clean up file if database operation fails
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/file/{file_id}")
async def get_file_metadata(file_id: str):
    """Get file metadata by file_id"""
    db = get_database()
    if db is None:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    file_data = await db["files"].find_one({"file_id": file_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Convert ObjectId to string for JSON serialization
    if "_id" in file_data:
        file_data["_id"] = str(file_data["_id"])
    
    return file_data
