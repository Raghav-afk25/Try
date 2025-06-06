from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from yt_dlp import YoutubeDL
import os

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "extractor_args": {"youtube": ["player_client=android"]},  # Bypass login & CAPTCHA
    "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
    "cachedir": False,
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}


@app.get("/")
async def root():
    return {"status": "OK", "usage": "/download/song/{video_id}"}


@app.get("/download/song/{video_id}")
async def download_song(video_id: str):
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            filename = filename.rsplit(".", 1)[0] + ".mp3"

        if os.path.exists(filename):
            return FileResponse(
                filename,
                media_type="audio/mpeg",
                filename=os.path.basename(filename)
            )
        else:
            return JSONResponse(status_code=404, content={"error": "File not found after download."})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
