from pathlib import Path
from typing import Optional
import os
import shutil
from app.utils.db import get_database

class FileService:
    def __init__(self):
        self.upload_dir = Path("temp_uploads")
        self.upload_dir.mkdir(exist_ok=True)
    
    async def get_file_by_id(self, file_id: str) -> Optional[dict]:
        """Get file metadata from database"""
        db = get_database()
        if db is None:
            return None
        return await db["files"].find_one({"file_id": file_id})
    
    async def update_file_status(self, file_id: str, status: str) -> bool:
        """Update file processing status"""
        db = get_database()
        if db is None:
            return False
        
        result = await db["files"].update_one(
            {"file_id": file_id},
            {"$set": {"status": status}}
        )
        return result.modified_count > 0
    
    def get_file_path(self, stored_filename: str) -> Path:
        """Get full path to stored file"""
        return self.upload_dir / stored_filename
    
    def file_exists(self, stored_filename: str) -> bool:
        """Check if file exists on disk"""
        return self.get_file_path(stored_filename).exists()
    
    def delete_file(self, stored_filename: str) -> bool:
        """Delete file from disk"""
        file_path = self.get_file_path(stored_filename)
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except OSError:
                return False
        return False
    
    async def cleanup_file(self, file_id: str) -> bool:
        """Remove file and metadata (cleanup after processing)"""
        # Get file metadata
        file_data = await self.get_file_by_id(file_id)
        if not file_data:
            return False
        
        # Delete file from disk
        self.delete_file(file_data["stored_filename"])
        
        # Remove from database
        db = get_database()
        if db is not None:
            await db["files"].delete_one({"file_id": file_id})
        
        return True
    
    async def extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    async def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            raise Exception("PyPDF2 not installed. Please install with: pip install PyPDF2")
        except Exception as e:
            raise Exception(f"Error extracting PDF text: {str(e)}")
    
    async def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from Word document"""
        try:
            import docx
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            raise Exception("python-docx not installed. Please install with: pip install python-docx")
        except Exception as e:
            raise Exception(f"Error extracting DOCX text: {str(e)}")