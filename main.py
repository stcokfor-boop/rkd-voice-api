import os
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
