from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "RKD Studio API is live and free!"}
