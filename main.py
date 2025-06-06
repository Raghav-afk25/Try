from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from yt_dlp import YoutubeDL
from pyrogram import Client
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
CACHE_CHANNEL = os.getenv("CACHE_CHANNEL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

app = FastAPI(title="DeadlineTech API")

templates = Jinja2Templates(directory="templates")

mongo = MongoClient(MONGO_URI)
db = mongo.ytmusic.files

bot = Client(
    "ytapi",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)
bot.start()

def get_audio_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "geo_bypass": True,
        "format": "bestaudio[ext=m4a]",
        "user_agent": "Mozilla/5.0"
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "id": info["id"],
            "title": info["title"],
            "url": info["webpage_url"]
        }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "owner": "@Smaugxd"})

@app.get("/download/song/{video_id}")
async def download_song(video_id: str):
    data = db.find_one({"video_id": video_id})
    if data:
        return {"status": "cached", "file_id": data["file_id"]}

    try:
        info = get_audio_info(video_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Video not found: {e}")

    file_name = f"{video_id}.m4a"
    ydl_opts = {
        "quiet": True,
        "geo_bypass": True,
        "format": "bestaudio[ext=m4a]",
        "outtmpl": file_name,
        "user_agent": "Mozilla/5.0"
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([info["url"]])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download error: {e}")

    msg = await bot.send_audio(CACHE_CHANNEL, audio=file_name, title=info["title"])
    db.insert_one({"video_id": video_id, "file_id": msg.audio.file_id})
    os.remove(file_name)

    return {"status": "ok", "file_id": msg.audio.file_id}

@app.post("/clear-cache")
async def clear_cache(api_key: str = Form(...)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    db.delete_many({})
    return {"status": "cache cleared"}

@app.post("/restart")
async def restart(api_key: str = Form(...)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    # Restart logic depends on your deployment setup
    return {"status": "restart requested - implement server restart manually or with process manager"}
