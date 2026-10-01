import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="RKD Studio Voice API", version="2.0")

# CORS Middleware (Aapki frontend website ke liye)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production mein yahan apni Vercel/Netlify URL de sakte hain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 1. DATABASE SETUP (SQLite) ─────────────────────────
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            credits INTEGER DEFAULT 1000000
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ── 2. TEMP MAIL BLOCKLIST ─────────────────────────────
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

# ── 3. REQUEST MODELS ──────────────────────────────────
class GenerateRequest(BaseModel):
    email: str
    text: str
    engine: str = "fish_speech"  # Options: fish_speech, f5_tts

class AdminCreditRequest(BaseModel):
    email: str
    amount: int
    admin_secret: str

# ── 4. VOICE GENERATION ENDPOINT ───────────────────────
@app.post("/generate")
def generate_voice(data: GenerateRequest):
    # Step A: Temp Mail Check
    if is_temp_mail(data.email):
        raise HTTPException(
            status_code=400, 
            detail="Temporary ya fake emails allowed nahi hain! Meherbani karke apni real email use karein."
        )
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # Step B: Check User and Credits
    cursor.execute("SELECT credits FROM users WHERE email = ?", (data.email,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(
            status_code=404, 
            detail="User registered nahi hai ya Rashid Khan Dashti ki taraf se credits allocate nahi kiye gaye."
        )
    
    current_credits = user[0]
    required_credits = max(len(data.text), 1) # 1 character = 1 credit
    
    if current_credits < required_credits:
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail=f"Aapke credits khatam ho chuke hain! Required: {required_credits}, Available: {current_credits}."
        )
    
    # Step C: Deduct Credits
    new_credits = current_credits - required_credits
    cursor.execute("UPDATE users SET credits = ? WHERE email = ?", (new_credits, data.email))
    conn.commit()
    conn.close()
    
    # Step D: Model Processing Logic (Fish Speech / F5-TTS Handler)
    # Yahan aap apne Fish Speech ya F5-TTS model ka inference code run karenge.
    selected_engine = data.engine
    
    return {
        "status": "success",
        "message": f"Audio successfully generated using {selected_engine}!",
        "engine_used": selected_engine,
        "remaining_credits": new_credits
    }

# ── 5. ADMIN ENDPOINT TO GRANT CREDITS ─────────────────
@app.post("/admin/add-credits")
def add_credits(data: AdminCreditRequest):
    # Secret password check taake koi aur access na kar sake
    if data.admin_secret != "rashidkhanfaizankhan@#$":
        raise HTTPException(status_code=403, detail="Unauthorized Admin Access!")
        
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # User create karein agar pehle se nahi hai, warna credits add kar dein
    cursor.execute("INSERT OR IGNORE INTO users (email, credits) VALUES (?, 0)", (data.email,))
    cursor.execute("UPDATE users SET credits = credits + ? WHERE email = ?", (data.amount, data.email))
    conn.commit()
    
    cursor.execute("SELECT credits FROM users WHERE email = ?", (data.email,))
    updated_credits = cursor.fetchone()[0]
    conn.close()
    
    return {
        "status": "success",
        "email": data.email,
        "added_credits": data.amount,
        "total_credits": updated_credits
    }

@app.get("/")
def home():
    return {"status": "Online", "platform": "RKD STUDIO AI by Rashid Khan Dashti"}
