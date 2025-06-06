import os
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client
from pyrogram.types import InputFile
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Env variables
MONGO_URL = os.getenv("MONGO_URL")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CDN_CHANNEL = int(os.getenv("CDN_CHANNEL"))

# Setup
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["ytmusic"]
collection = db["songs"]

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_event("startup")
async def startup_event():
    await bot.start()

@app.on_event("shutdown")
async def shutdown_event():
    await bot.stop()

@app.get("/download/song/{video_id}")
async def download_song(video_id: str):
    existing = await collection.find_one({"_id": video_id})
    if existing:
        return {"file_id": existing["file_id"]}

    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{video_id}.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "user_agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/89.0.4389.90 Mobile Safari/537.36",
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        sent = await bot.send_audio(
            chat_id=CDN_CHANNEL,
            audio=InputFile(file_path),
            title=info.get("title", "Unknown"),
            duration=int(info.get("duration", 0)),
        )

        await collection.insert_one({"_id": video_id, "file_id": sent.audio.file_id})
        os.remove(file_path)

        return {"file_id": sent.audio.file_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
