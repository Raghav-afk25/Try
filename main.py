import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from yt_dlp import YoutubeDL
from pyrogram import Client
from pyrogram.types import InputFile
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

app = FastAPI()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CDN_CHANNEL = int(os.getenv("CDN_CHANNEL"))
MONGO_URL = os.getenv("MONGO_URL")

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["ytmusic"]["songs"]

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_event("startup")
async def start():
    await bot.start()

@app.on_event("shutdown")
async def stop():
    await bot.stop()

@app.get("/download/song/{video_id}")
async def download(video_id: str):
    cached = await db.find_one({"_id": video_id})
    if cached:
        return {"file_id": cached["file_id"], "cached": True}

    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": f"{video_id}.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "user_agent": "Mozilla/5.0 (Linux; Android 10)",
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        msg = await bot.send_audio(
            chat_id=CDN_CHANNEL,
            audio=InputFile(file_path),
            title=info.get("title"),
            duration=info.get("duration")
        )

        await db.insert_one({"_id": video_id, "file_id": msg.audio.file_id})
        os.remove(file_path)

        return {"file_id": msg.audio.file_id, "cached": False}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
