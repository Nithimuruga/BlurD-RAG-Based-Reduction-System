from datetime import datetime
from typing import Optional

class FileModel:
    def __init__(
        self,
        user_id: str,
        file_id: str,
        original_filename: str,
        stored_filename: str,
        file_type: str,
        file_size: int,
        status: str = "uploaded",
        upload_time: Optional[datetime] = None,
        file_path: str = ""
    ):
        self.user_id = user_id
        self.file_id = file_id
        self.original_filename = original_filename
        self.stored_filename = stored_filename
        self.file_type = file_type
        self.file_size = file_size
        self.status = status
        self.upload_time = upload_time or datetime.utcnow()
        self.file_path = file_path

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "file_id": self.file_id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status,
            "upload_time": self.upload_time,
            "file_path": self.file_path
        }