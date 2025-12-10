from fastapi import APIRouter, HTTPException
from app.services.extractor import extract_text
from app.utils.db import get_database
import os

router = APIRouter(prefix="/extract", tags=["Extract"])

@router.post("/{file_id}")
async def extract_file(file_id: str):
    db = get_database()
    file_meta = await db["files"].find_one({"file_id": file_id})
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = os.path.join("temp_uploads", file_meta["filename"])
    file_type = file_meta["type"].split("/")[-1].lower()
    try:
        result = await extract_text(file_path, file_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Optionally, update status in DB
    await db["files"].update_one({"file_id": file_id}, {"$set": {"status": "extracted"}})
    return {"file_id": file_id, "extraction": result}
