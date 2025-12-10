# File Upload API Documentation

## Overview

The FastAPI upload router provides secure file upload functionality with MongoDB metadata storage for document processing workflows.

## Endpoint: `/upload/`

### Method: POST

### Description

Uploads files and stores metadata in MongoDB. Supports PDF, DOCX, XLSX, JPG, and PNG files.

### Request Parameters

**Form Data:**

- `user_id` (str, required): User identifier
- `file` (UploadFile, required): File to upload

### Supported File Types

| File Type         | MIME Type                                                                 | Extensions      |
| ----------------- | ------------------------------------------------------------------------- | --------------- |
| PDF               | `application/pdf`                                                         | `.pdf`          |
| Word Document     | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx`         |
| Excel Spreadsheet | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`       | `.xlsx`         |
| JPEG Image        | `image/jpeg`                                                              | `.jpg`, `.jpeg` |
| PNG Image         | `image/png`                                                               | `.png`          |

### File Constraints

- **Maximum File Size:** 50MB
- **Minimum File Size:** Must not be empty
- **File Extension:** Must match MIME type

### Response

**Success (200):**

```json
{
  "file_id": "uuid-string",
  "message": "File uploaded successfully",
  "filename": "original_filename.ext",
  "file_size": 1024
}
```

**Error Responses:**

- `400 Bad Request`: Invalid file type, extension mismatch, or empty file
- `413 Payload Too Large`: File exceeds 50MB limit
- `500 Internal Server Error`: Database connection or file system error

### MongoDB Document Structure

Files are stored in the `files` collection with the following schema:

```json
{
  "_id": "mongodb-object-id",
  "user_id": "user123",
  "file_id": "uuid-string",
  "original_filename": "document.pdf",
  "stored_filename": "uuid.pdf",
  "file_type": "application/pdf",
  "file_size": 1024,
  "status": "uploaded",
  "upload_time": "2025-10-03T10:30:00Z",
  "file_path": "temp_uploads/uuid.pdf"
}
```

## Endpoint: `/upload/file/{file_id}`

### Method: GET

### Description

Retrieves file metadata by file ID.

### Response

Returns the complete MongoDB document for the specified file.

## File Storage

- **Location:** `temp_uploads/` directory
- **Naming:** Files are stored with UUID filenames to prevent conflicts
- **Cleanup:** Use `FileService.cleanup_file()` to remove files after processing

## Usage Examples

### Python (requests)

```python
import requests

# Upload file
url = "http://localhost:8000/upload/"
files = {"file": ("document.pdf", open("document.pdf", "rb"), "application/pdf")}
data = {"user_id": "user123"}

response = requests.post(url, files=files, data=data)
file_id = response.json()["file_id"]

# Get metadata
metadata = requests.get(f"http://localhost:8000/upload/file/{file_id}")
```

### curl

```bash
# Upload file
curl -X POST "http://localhost:8000/upload/" \
  -F "user_id=user123" \
  -F "file=@document.pdf"

# Get metadata
curl -X GET "http://localhost:8000/upload/file/{file_id}"
```

### JavaScript (FormData)

```javascript
const formData = new FormData();
formData.append("user_id", "user123");
formData.append("file", fileInput.files[0]);

fetch("/upload/", {
  method: "POST",
  body: formData,
})
  .then((response) => response.json())
  .then((data) => console.log(data.file_id));
```

## Error Handling

The API provides detailed error messages for common issues:

- **Invalid file type**: Lists allowed formats
- **Extension mismatch**: Ensures file extension matches MIME type
- **File too large**: Specifies maximum size limit
- **Database errors**: Provides connection failure details

## Dependencies

Required Python packages:

- `fastapi`: Web framework
- `motor`: Async MongoDB driver
- `aiofiles`: Async file operations
- `python-multipart`: Form data parsing
- `uuid`: File ID generation

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Start MongoDB: `mongod`
3. Run FastAPI: `uvicorn app.main:app --reload`
4. Test upload: `python test_upload.py`

## Security Considerations

- File type validation prevents malicious uploads
- File size limits prevent DoS attacks
- UUID filenames prevent directory traversal
- Temporary storage allows for cleanup after processing
- Content-Type verification ensures file integrity
