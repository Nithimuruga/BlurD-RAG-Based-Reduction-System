"""
Minimal server for debugging shutdown issue
"""
from fastapi import FastAPI
import uvicorn
import logging
import signal
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.get("/")
def root():
    return {"message": "Minimal server running"}

@app.get("/health")  
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    logger.info("Starting minimal server...")
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="info")