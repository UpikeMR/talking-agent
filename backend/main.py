from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from google.cloud import texttospeech
import os
import io

app = FastAPI(title="Talking Agent Backend")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],  # Allow all common methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["Content-Disposition"],
    max_age=86400,
)

# Write TTS credentials to a temporary file
tts_credentials_json = os.getenv("TTS_CREDENTIALS_JSON")
if tts_credentials_json:
    with open("/tmp/tts-credentials.json", "w") as f:
        f.write(tts_credentials_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/tts-credentials.json"
else:
    print("WARNING: TTS_CREDENTIALS_JSON environment variable not set")

# Configure APIs with environment variables
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY environment variable not set")
else:
    genai.configure(api_key=api_key)

# Simple health check endpoints
@app.get("/")
async def root():
    return {"status": "online", "message": "Talking Agent Backend is running"}

@app.get("/test")
async def test():
    return {"status": "ok", "message": "Backend is running and CORS should be working"}

# Handle OPTIONS request explicitly for all routes
@app.options("/{full_path:path}")
async def options_route(request: Request):
    return JSONResponse(
        content={"detail": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS, PUT, DELETE",
            "Access-Control-Allow-Headers": "*",
        }
    )

# The main conversation endpoint that handles audio processing
@app.post("/conversation")
async def conversation(audio: UploadFile = File(...)):
    """
    Receives an audio file, processes it with the talking-agent assistant,
    and returns a .wav audio response.
    """
    try:
        # Read the uploaded audio file
        audio_data = await audio.read()
        
        # Log file information
        print(f"Received file: {audio.filename} with content type: {audio.content_type}")
        
        # Check for API key
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        
        # Initialize Gemini model
        try:
            model = genai.GenerativeModel("talking-agent")
        except Exception as model_error:
            raise HTTPException(status_code=500, 
                             detail=f"Failed to initialize Gemini model: {str(model_error)}")
        
        # Process with Gemini
        try:
            response = model.generate_content(audio_data)
            if not response.text:
                raise HTTPException(status_code=500, detail="No response from AI assistant")
            text = response.text
            print(f"Generated response text: {text[:100]}...")  # Log first 100 chars
        except Exception as gemini_error:
            raise HTTPException(status_code=500, 
                             detail=f"Error processing with Gemini: {str(gemini_error)}")

        # Text-to-Speech conversion
        try:
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
            print(f"Generated audio response of {len(tts_response.audio_content)} bytes")
        except Exception as tts_error:
            raise HTTPException(status_code=500, 
                             detail=f"Error with Text-to-Speech: {str(tts_error)}")

        # Stream the audio response
        audio_stream = io.BytesIO(tts_response.audio_content)
        return StreamingResponse(
            audio_stream,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=response.wav",
                "Access-Control-Allow-Origin": "*"
            }
        )

    except Exception as e:
        print(f"Error in /conversation endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# Start the server if run directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)