from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from google.cloud import texttospeech
import os
import io
import json

app = FastAPI(title="Talking Agent Backend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow the front-end domain
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Write TTS credentials to a temporary file
tts_credentials_json = os.getenv("TTS_CREDENTIALS_JSON")
if tts_credentials_json:
    with open("/tmp/tts-credentials.json", "w") as f:
        f.write(tts_credentials_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/tts-credentials.json"
else:
    raise ValueError("TTS_CREDENTIALS_JSON environment variable not set")

# Configure APIs with environment variables
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("talking-agent")
tts_client = texttospeech.TextToSpeechClient()

@app.post("/conversation")
async def conversation(audio: UploadFile = File(...)):
    """
    Receives a .wav file, processes it with the talking-agent assistant,
    and returns a .wav audio response.
    """
    try:
        # Read the uploaded .wav file
        audio_data = await audio.read()
        if not audio.filename.endswith(".wav"):
            raise HTTPException(status_code=400, detail="Only .wav files are supported")

        # Send audio to Gemini API (talking-agent assistant)
        response = model.generate_content(audio_data)
        if not response.text:
            raise HTTPException(status_code=500, detail="No response from AI assistant")
        text = response.text

        # Convert text to .wav using Google Text-to-Speech
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

        # Return the .wav audio as a streaming response
        audio_stream = io.BytesIO(tts_response.audio_content)
        return StreamingResponse(
            audio_stream,
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=response.wav"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")