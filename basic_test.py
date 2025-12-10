from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def root():
    return {"test": "working"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    print("Starting basic test server...")
    uvicorn.run(app, host="127.0.0.1", port=8002)