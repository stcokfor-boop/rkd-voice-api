import os
import sqlite3
import base64
import asyncio
import tempfile
import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="RKD Studio Voice API", version="3.0")

# ── CORS ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── VOICES MAP ─────────────────────────────────────────
VOICES = {
    "english_male":   "en-US-GuyNeural",
    "english_female": "en-US-JennyNeural",
    "urdu_male":      "ur-PK-AsadNeural",
    "urdu_female":    "ur-PK-UzmaNeural",
    "hindi_male":     "hi-IN-MadhurNeural",
    "hindi_female":   "hi-IN-SwaraNeural",
    "arabic_male":    "ar-SA-HamedNeural",
    "arabic_female":  "ar-SA-ZariyahNeural",
    # Default
    "default":        "en-US-JennyNeural",
}

# ── DATABASE ───────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            credits INTEGER DEFAULT 1000000
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ── TEMP MAIL BLOCK ────────────────────────────────────
BLOCKED_DOMAINS = [
    "mailinator.com", "10minutemail.com", "guerrillamail.com",
    "tempmail.com", "trashmail.com", "yopmail.com", "dispostable.com",
    "getnada.com", "sharklasers.com", "temp-mail.org", "fakemail.com"
]

def is_temp_mail(email: str) -> bool:
    try:
        domain = email.split("@")[1].strip().lower()
        return domain in BLOCKED_DOMAINS
    except Exception:
        return True

# ── MODELS ─────────────────────────────────────────────
class GenerateRequest(BaseModel):
    email: str
    text: str
    engine: str = "edge_tts"
    voice: str = "urdu_female"

class AdminCreditRequest(BaseModel):
    email: str
    amount: int
    admin_secret: str

# ── VOICE GENERATION ───────────────────────────────────
async def generate_edge_tts(text: str, voice_key: str) -> str:
    voice = VOICES.get(voice_key, VOICES["default"])
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        output_path = tmp.name

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

    with open(output_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    os.unlink(output_path)
    return audio_b64

# ── GENERATE ENDPOINT ──────────────────────────────────
@app.post("/generate")
async def generate_voice(data: GenerateRequest):

    # Temp mail check
    if is_temp_mail(data.email):
        raise HTTPException(
            status_code=400,
            detail="Temporary email allowed nahi! Real email use karein."
        )

    # User aur credits check
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT credits FROM users WHERE email = ?", (data.email,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="User registered nahi hai. Pehle Rashid Khan se credits lein: 03441038422"
        )

    current_credits = user[0]
    required_credits = max(len(data.text), 1)

    if current_credits < required_credits:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Credits khatam! Chahiye: {required_credits}, Baqi: {current_credits}. Contact: 03441038422"
        )

    # Credits deduct
    new_credits = current_credits - required_credits
    cursor.execute(
        "UPDATE users SET credits = ? WHERE email = ?",
        (new_credits, data.email)
    )
    conn.commit()
    conn.close()

    # Voice generate karo
    try:
        audio_b64 = await generate_edge_tts(data.text, data.voice)
    except Exception as e:
        # Error aya toh credits wapas karo
        conn2 = sqlite3.connect("users.db")
        conn2.execute(
            "UPDATE users SET credits = credits + ? WHERE email = ?",
            (required_credits, data.email)
        )
        conn2.commit()
        conn2.close()
        raise HTTPException(status_code=500, detail=f"Voice error: {str(e)}")

    return {
        "status": "success",
        "message": "✅ Voice generate ho gayi!",
        "engine_used": "Microsoft Edge TTS Neural",
        "voice_used": VOICES.get(data.voice, VOICES["default"]),
        "remaining_credits": new_credits,
        "audio": audio_b64,
        "format": "mp3"
    }

# ── ADMIN ENDPOINT ─────────────────────────────────────
@app.post("/admin/add-credits")
def add_credits(data: AdminCreditRequest):
    if data.admin_secret != "rashidkhanfaizankhan@#$":
        raise HTTPException(status_code=403, detail="Unauthorized!")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (email, credits) VALUES (?, 0)",
        (data.email,)
    )
    cursor.execute(
        "UPDATE users SET credits = credits + ? WHERE email = ?",
        (data.amount, data.email)
    )
    conn.commit()
    cursor.execute("SELECT credits FROM users WHERE email = ?", (data.email,))
    updated = cursor.fetchone()[0]
    conn.close()

    return {
        "status": "success",
        "email": data.email,
        "added_credits": data.amount,
        "total_credits": updated
    }

# ── CHECK CREDITS ──────────────────────────────────────
@app.get("/credits/{email}")
def check_credits(email: str):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT credits FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="User nahi mila!")

    return {"email": email, "credits": user[0]}

# ── HOME ───────────────────────────────────────────────
@app.get("/")
def home():
    return {
        "status": "Online",
        "platform": "RKD STUDIO AI by Rashid Khan Dashti",
        "version": "3.0",
        "engine": "Microsoft Edge TTS Neural",
        "voices": list(VOICES.keys())
    }
