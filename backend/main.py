from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from google.cloud import texttospeech
import os
import io

app = FastAPI(title="Talking Agent Backend")

# More detailed CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Explicitly list the methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["Content-Disposition"],  # Expose headers needed for response
    max_age=86400,  # Cache preflight requests for 24 hours
)

# Write TTS credentials to a temporary file
tts_credentials_json = os.getenv("TTS_CREDENTIALS_JSON")
if tts_credentials_json:
    with open("/tmp/tts-credentials.json", "w") as f:
        f.write(tts_credentials_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/tts-credentials.json"
else:
    print("WARNING: TTS_CREDENTIALS_JSON environment variable not set")
    # Don't raise error here to allow the application to start

# Configure APIs with environment variables
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY environment variable not set")
else:
    genai.configure(api_key=api_key)

# Add a simple test endpoint
@app.get("/")
async def root():
    return {"status": "online", "message": "Talking Agent Backend is running"}

@app.get("/test")
async def test():
    return {"status": "ok", "message": "Backend is running and CORS should be working"}

# Add OPTIONS method handler for the conversation endpoint to support preflight requests
@app.options("/conversation")
async def options_conversation():
    return {}

@app.post("/conversation")
async def conversation(audio: UploadFile = File(...)):
    """
    Receives a .wav file, processes it with the talking-agent assistant,
    and returns a .wav audio response.
    """
    try:
        # Read the uploaded .wav file
        audio_data = await audio.read()
        
        # More permissive file type checking
        if not (audio.filename.endswith(".wav") or 
                audio.content_type in ["audio/wav", "audio/wave", "audio/x-wav", 
                                     "audio/webm", "audio/ogg", "audio/mpeg"]):
            print(f"Received file: {audio.filename} with content type: {audio.content_type}")
            # Continue anyway but log the issue
        
        # Initialize needed clients only when required
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        
        try:
            model = genai.GenerativeModel("talking-agent")
        except Exception as model_error:
            raise HTTPException(status_code=500, 
                             detail=f"Failed to initialize Gemini model: {str(model_error)}")
        
        # Send audio to Gemini API (talking-agent assistant)
        try:
            response = model.generate_content(audio_data)
            if not response.text:
                raise HTTPException(status_code=500, detail="No response from AI assistant")
            text = response.text
        except Exception as gemini_error:
            raise HTTPException(status_code=500, 
                             detail=f"Error processing with Gemini: {str(gemini_error)}")

        # Convert text to .wav using Google Text-to-Speech
        try:
            tts_client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16  # .wav format
            )
            tts_response = tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
        except Exception as tts_error:
            raise HTTPException(status_code=500, 
                             detail=f"Error with Text-to-Speech: {str(tts_error)}")

        # Return the .wav audio as a streaming response
        audio_stream = io.BytesIO(tts_response.audio_content)
        return StreamingResponse(
            audio_stream,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=response.wav",
                "Access-Control-Allow-Origin": "*"  # Additional CORS header in response
            }
        )

    except Exception as e:
        print(f"Error in /conversation endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# If this file is run directly, start the server
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)