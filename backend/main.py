from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from google.cloud import texttospeech
import os
import io
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Talking Agent Backend")

# Configure CORS - be very permissive for troubleshooting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",  # Allow all origins with regex
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load credentials and configure APIs
try:
    tts_credentials_json = os.getenv("TTS_CREDENTIALS_JSON")
    if tts_credentials_json:
        with open("/tmp/tts-credentials.json", "w") as f:
            f.write(tts_credentials_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/tts-credentials.json"
        logger.info("TTS credentials loaded")
    else:
        logger.warning("TTS_CREDENTIALS_JSON environment variable not set")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured")
    else:
        logger.warning("GEMINI_API_KEY environment variable not set")
except Exception as e:
    logger.error(f"Error during initialization: {str(e)}")

# Add a middleware to add CORS headers to every response
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    try:
        response = await call_next(request)
        # Add CORS headers to every response
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    except Exception as e:
        logger.error(f"Middleware error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )

# Health check endpoint
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"status": "online", "message": "Talking Agent Backend is running"}

@app.get("/test")
async def test():
    logger.info("Test endpoint accessed")
    return {"status": "ok", "message": "Backend is running and CORS should be working"}

# Handle OPTIONS preflight requests
@app.options("/{path:path}")
async def options_route(path: str):
    logger.info(f"OPTIONS request received for path: {path}")
    return JSONResponse(
        content={"detail": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

# Main conversation endpoint
@app.post("/conversation")
async def conversation(audio: UploadFile = File(...)):
    """Process audio and return synthesized speech response"""
    logger.info(f"Conversation endpoint called with file: {audio.filename}, content-type: {audio.content_type}")
    
    try:
        # Read audio data
        audio_data = await audio.read()
        logger.info(f"Received audio data of size: {len(audio_data)} bytes")
        
        # Check for API key
        if not os.getenv("GEMINI_API_KEY"):
            logger.error("GEMINI_API_KEY not configured")
            return JSONResponse(
                status_code=500, 
                content={"detail": "GEMINI_API_KEY not configured"},
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Use Gemini to process audio
        logger.info("Initializing Gemini model")
        model = genai.GenerativeModel("talking-agent")
        
        logger.info("Processing audio with Gemini")
        response = model.generate_content(audio_data)
        if not response.text:
            logger.error("No response text from Gemini")
            return JSONResponse(
                status_code=500, 
                content={"detail": "No response from AI assistant"},
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        text = response.text
        logger.info(f"Generated text response: {text[:100]}...")
        
        # Convert text to speech
        logger.info("Converting text to speech")
        tts_client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )
        
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        
        logger.info(f"Generated audio of size: {len(tts_response.audio_content)} bytes")
        
        # Return audio response
        audio_stream = io.BytesIO(tts_response.audio_content)
        return StreamingResponse(
            audio_stream,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=response.wav",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )
    
    except Exception as e:
        logger.error(f"Error in conversation endpoint: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error processing request: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )

# For running locally
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)