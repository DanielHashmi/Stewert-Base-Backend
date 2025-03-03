import os
import uuid
import base64
import google.generativeai as genai
import edge_tts
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://base-backend-nu.vercel.app",
                   "http://localhost:3000", 'https://base-mauve.vercel.app/', os.getenv('FRONTEND_URL')],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("WARNING: GOOGLE_API_KEY not found in environment variables")
genai.configure(api_key=GOOGLE_API_KEY)


class Command(BaseModel):
    text: str


async def generate_audio(text: str, filename: str):
    try:
        communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
        await communicate.save(filename)
        return True
    except Exception as e:
        print(f"Error generating audio: {e}")
        return False


@app.post("/command/")
async def process_command(command: Command, background_tasks: BackgroundTasks):
    try:
        user_input = command.text

        if not GOOGLE_API_KEY:
            return {"response": "Backend API key not configured", "audio": None}

        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                f"You are Stewart Base, a voice assistant created by (Daniel Hashmi, he is a web developer, programmer and he is the founder of DanielCodeForge a learning resource platform). "
                f"User's prompt: {user_input}. Respond briefly without punctuation."
            )
            text_response = response.candidates[0].content.parts[
                0].text if response.candidates else "I didn't understand that."
        except Exception as e:
            print(f"Error with Gemini API: {e}")
            text_response = "Sorry, I'm having trouble connecting to my brain right now."

        # Generate a unique filename in the /tmp directory for Vercel compatibility
        tmp_dir = "/tmp" if os.path.exists("/tmp") else "."
        filename = os.path.join(tmp_dir, f"output_{uuid.uuid4()}.mp3")

        audio_success = await generate_audio(text_response, filename)

        if not audio_success or not os.path.exists(filename):
            return {"response": text_response, "audio": None}

        with open(filename, "rb") as audio_file:
            audio_bytes = audio_file.read()
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        audio_data_url = f"data:audio/mpeg;base64,{audio_base64}"

        background_tasks.add_task(os.remove, filename)
        return {"response": text_response, "audio": audio_data_url}

    except Exception as e:
        print(f"Unhandled error in process_command: {e}")
        return {"response": "I encountered an unexpected error.", "audio": None}
