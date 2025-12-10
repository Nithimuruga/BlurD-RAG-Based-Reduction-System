from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import example_router, upload_router, detection_router, pii_router
from app.utils.db import connect_to_mongo, close_mongo_connection
import logging
import os

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    # Pre-warm detection orchestrator and load ML models once at startup
    try:
        # Import here to avoid any circular import surprises
        from app.routers.detection_router import get_detection_orchestrator
        orchestrator = await get_detection_orchestrator()
        await orchestrator.initialize()
        logger.info("Pre-warmed detection orchestrator and models at startup")
        
        # Initialize PII detection components
        from app.services.detection_orchestrator import DetectionOrchestrator
        pii_orchestrator = DetectionOrchestrator()
        await pii_orchestrator.initialize()
        logger.info("PII detection system initialized")
    except Exception as e:
        logger.warning(f"Detector pre-warm failed (will lazy-load on first request): {e}")
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:3000",  # React (Create React App)
    "http://localhost:5173",  # Vite development server
    "http://127.0.0.1:5173",  # Vite with 127.0.0.1
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(example_router.router)
app.include_router(upload_router.router)
app.include_router(detection_router.router)
app.include_router(pii_router.pii_router)

# Ensure redacted outputs directory exists
os.makedirs("redacted_outputs", exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "FastAPI + MongoDB + CORS scaffold ready!"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "API is running",
        "cors": "enabled"
    }
