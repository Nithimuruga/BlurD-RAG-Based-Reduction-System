from fastapi import APIRouter
from app.services.example_service import get_example

router = APIRouter(prefix="/example", tags=["Example"])

@router.get("/")
def example_endpoint():
    return get_example()
