Talking Agent

A voice-driven conversational AI application that integrates with a custom assistant ("talking-agent") built on Google AI Studio. Users can speak into a microphone, and the assistant responds with seamless audio replies in .wav format. The app features a clean, modern front-end styled with Tailwind CSS and a Python back-end, all hosted on Render without a database.

Project Structure
talking-agent/
frontend/                  # Static front-end files
index.html            # Main UI with mic and speaker
script.js             # Handles audio recording and playback
styles/               # Optional custom CSS
custom.css        # Placeholder for additional styles
backend/                  # Python back-end service
main.py               # API to connect front-end and Google AI Studio
requirements.txt      # Python dependencies
.env                  # Local API keys (not committed)
README.md                 # This file
.gitignore                # Git ignore rules

Features

Voice Interaction: Speak via microphone, get .wav audio responses.
Custom AI: Uses a pre-trained "talking-agent" assistant on Google AI Studio with stored knowledge.
Clean Design: Front-end styled with Tailwind CSS for a sleek, user-friendly look.
No Database: Knowledge is embedded in the AI assistant, not stored locally.
Render Hosting: Deployed as a static front-end and Python web service.
Prerequisites

Google Cloud Account: For API keys (Gemini API, Text-to-Speech).
Google AI Studio: Custom assistant named "talking-agent" with uploaded data.
Render Account: For hosting the app.
Git: For version control and deployment.
Python 3.9+: For back-end development.
Node.js/npm (optional): Only if you add JS dependencies later.
Setup Instructions

Local Development

Clone the Repository (if already on Git): git clone <repository-url> cd talking-agent Or create the structure manually in ~/Documents/talking-agent/.
Front-End Setup:
Navigate to frontend/.
Open index.html in a browser to test the UI (Tailwind CSS is included via CDN).
Back-End Setup:
Navigate to backend/.
Create a virtual environment: python -m venv venv source venv/bin/activate # On Windows: venv\Scripts\activate
Install dependencies: pip install -r requirements.txt
Create a .env file with your API keys: GEMINI_API_KEY=your-gemini-api-key TTS_API_KEY=your-text-to-speech-api-key
Run the server: uvicorn main:app --reload
Test Locally:
Open http://localhost:8000 (back-end) and frontend/index.html in a browser.
Ensure the front-end can send audio to http://localhost:8000/conversation.
Google AI Studio Assistant

Go to ai.studio.google.com.
Create an assistant named "talking-agent".
Upload all relevant data (e.g., text, PDFs) to embed knowledge.
Set the prompt: "Use your knowledge and respond to the verbalized question."
Get the model ID or API endpoint for use in backend/main.py.
Deployment on Render

Prepare Repositories:
Push the project to a GitHub repo (or two separate repos for frontend/ and backend/).
Front-End Deployment:
In Render, create a new Static Site.
Connect your GitHub repo (or frontend/ subfolder).
Set the build command to echo "No build required" (static files only).
Deploy and note the URL (e.g., https://talking-agent-frontend.onrender.com).
Back-End Deployment:
In Render, create a new Web Service.
Connect your GitHub repo (or backend/ subfolder).
Set the runtime to Python.
Set the start command: uvicorn main:app --host 0.0.0.0 --port 8000.
Add environment variables:
GEMINI_API_KEY: Your Gemini API key.
TTS_API_KEY: Your Text-to-Speech API key.
Deploy and note the URL (e.g., https://talking-agent-backend.onrender.com).
Connect Front-End to Back-End:
Update frontend/script.js to point to the back-end URL (e.g., fetch('https://talking-agent-backend.onrender.com/conversation')).
Test Deployment:
Visit the front-end URL, speak into the mic, and verify the .wav response plays.
Usage

Open the deployed front-end in a browser.
Click the microphone button to record a question.
Wait for the AI's .wav response to play automatically.
Notes

API Keys: Store them securely in Render's environment variables, not in .env for production.
Latency: Optimize audio processing for seamless conversations; test with short and long inputs.
Troubleshooting: Check Render logs or local server output if audio fails.
License
This project is for personal use. Modify as needed!