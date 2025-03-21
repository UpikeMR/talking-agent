from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from google.cloud import texttospeech
import os
import io
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Talking Agent")

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

# Mount static files directory
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# API routes
@app.get("/api/test")
async def test():
    logger.info("Test endpoint accessed")
    return {"status": "ok", "message": "API is running"}

@app.post("/api/conversation")
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
                content={"detail": "GEMINI_API_KEY not configured"}
            )
        
        # Use Gemini to process audio - THIS IS THE PROBLEM AREA
        logger.info("Initializing Gemini model")
        model = genai.GenerativeModel("talking-agent")
        
        # Convert audio data to the proper format for Gemini
        # The model expects a properly structured content object with the audio data
        content = [
            {
                "mime_type": audio.content_type,
                "data": audio_data
            }
        ]
        
        logger.info("Processing audio with Gemini")
        response = model.generate_content(content)  # Pass the structured content
        if not response.text:
            logger.error("No response text from Gemini")
            return JSONResponse(
                status_code=500, 
                content={"detail": "No response from AI assistant"}
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
            headers={"Content-Disposition": "inline; filename=response.wav"}
        )
    
    except Exception as e:
        logger.error(f"Error in conversation endpoint: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error processing request: {str(e)}"}
        )

# Serve the main HTML page
@app.get("/")
async def serve_index():
    return FileResponse(static_dir / "index.html")

# For running locally
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)