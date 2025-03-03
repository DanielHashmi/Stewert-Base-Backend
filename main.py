import os
import uuid
import base64
import google.generativeai as genai
import edge_tts
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
# from elevenlabs.client import ElevenLabs
# from elevenlabs import VoiceSettings

load_dotenv()
# client = ElevenLabs(api_key=os.getenv("ELEVEN_LABS_API_KEY"))
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL"), 'http://localhost:3000'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)


class Command(BaseModel):
    text: str

# def text_to_speech_file(text: str, filename: str) -> str:
#     response = client.text_to_speech.convert(
#         voice_id='JBFqnCBsd6RMkjVDRZzb',
#         output_format="mp3_22050_32",
#         text=text,
#         model_id="eleven_turbo_v2_5",
#     )
#     with open(filename, "wb") as f:
#         for chunk in response:
#             if chunk:
#                 f.write(chunk)
#     return filename


async def generate_audio(text: str, filename: str):
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await communicate.save(filename)
    # elif voice == 'natural':
    #     text_to_speech_file(text, filename)


@app.post("/command/")
async def process_command(command: Command, background_tasks: BackgroundTasks):
    user_input = command.text

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        f"You are Stewart Base, a voice assistant created by (Daniel Hashmi, he is a web developer, programmer and he is the founder of DanielCodeForge a learning resource platform). "
        f"User's prompt: {user_input}. Respond briefly without punctuation."
    )

    text_response = response.candidates[0].content.parts[0].text if response.candidates else "I didn't understand that."

    filename = f"output_{uuid.uuid4()}.mp3"
    await generate_audio(text_response, filename)

    if not os.path.exists(filename):
        raise HTTPException(
            status_code=500, detail="Failed to generate audio file")

    with open(filename, "rb") as audio_file:
        audio_bytes = audio_file.read()
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    audio_data_url = f"data:audio/mpeg;base64,{audio_base64}"

    background_tasks.add_task(os.remove, filename)
    return {"response": text_response, "audio": audio_data_url}
