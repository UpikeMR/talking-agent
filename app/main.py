from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
import io
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Talking Agent Proxy")

# Allow CORS if your front-end is served from a different domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict this to your front-end URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (e.g., index.html, script.js, custom CSS)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Cloud Run service endpoint URL (replace with your actual Cloud Run URL)
CLOUD_RUN_URL = "https://audio-processing-service-490280071789.us-east1.run.app/api/conversation"

@app.get("/api/test")
async def test():
    """Test endpoint to ensure connectivity to the Cloud Run service."""
    try:
        # Forward a test request to Cloud Run's /api/test endpoint (if available)
        async with httpx.AsyncClient() as client:
            # Assuming the Cloud Run service has a /api/test endpoint; adjust if needed.
            response = await client.get(CLOUD_RUN_URL.replace("/api/conversation", "/api/test"))
            if response.status_code == 200:
                return {"status": "ok", "message": "Proxy and Cloud Run service are operational"}
            else:
                return JSONResponse(status_code=response.status_code, content={"detail": "Cloud Run test failed"})
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/conversation")
async def conversation(audio: UploadFile = File(...)):
    """Proxy endpoint: forwards audio file to the Cloud Run audio processing service and streams back the audio response."""
    try:
        # Read the audio file from the client
        audio_data = await audio.read()
        logger.info(f"Proxy received audio: {audio.filename}, size: {len(audio_data)} bytes")
        
        # Prepare the file payload for the Cloud Run service
        files = {"audio": (audio.filename, audio_data, audio.content_type)}
        
        # Forward the audio file using an asynchronous HTTP client
        async with httpx.AsyncClient() as client:
            response = await client.post(CLOUD_RUN_URL, files=files)
        
        if response.status_code != 200:
            logger.error(f"Cloud Run service error: {response.status_code}")
            return JSONResponse(status_code=response.status_code, content={"detail": "Error from Cloud Run service"})
        
        # Stream the returned audio content to the client
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=response.wav"}
        )
    
    except Exception as e:
        logger.error(f"Proxy error: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": f"Error processing request: {str(e)}"})

@app.get("/")
async def serve_index():
    return FileResponse(static_dir / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
