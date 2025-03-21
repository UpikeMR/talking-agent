from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import google.generativeai as genai
from google.cloud import texttospeech
import os
import io

app = FastAPI(title="Talking Agent Backend")

# Configure APIs with environment variables
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("talking-agent")  # Your Google AI Studio assistant name
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
        response = model.generate_content(audio_data)  # Assumes audio input support
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

# Run with: uvicorn main:app --host 0.0.0.0 --port 8000