from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class TextToVoice(BaseModel):
    text: str

@app.get("/")
def home():
    return {"status": "RKD Studio Voice API is live and working!"}

@app.post("/generate")
def generate_audio(data: TextToVoice):
    return {
        "success": True,
        "text_received": data.text,
        "message": "Voice generation request received successfully!"
    }
