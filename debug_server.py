"""
Minimal FastAPI server to test basic functionality
"""
from fastapi import FastAPI
import logging
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Debug Server")

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Debug server is running"}

@app.get("/health")
async def health():
    logger.info("Health endpoint called")
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    logger.info("Server startup event triggered")

@app.on_event("shutdown") 
async def shutdown_event():
    logger.info("Server shutdown event triggered")

if __name__ == "__main__":
    logger.info("Starting debug server...")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")