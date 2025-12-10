from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FileUploadResponse(BaseModel):
    file_id: str
    message: str
    filename: str
    file_size: int

class FileMetadata(BaseModel):
    user_id: str
    file_id: str
    original_filename: str
    stored_filename: str
    file_type: str
    file_size: int
    status: str
    upload_time: datetime
    file_path: str