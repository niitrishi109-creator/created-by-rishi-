import re
import time
from pathlib import Path

import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "generated_audio"
AUDIO_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Rishi Voice AI")

VOICES = {
    "hi-female": "hi-IN-SwaraNeural",
    "hi-male": "hi-IN-MadhurNeural",
    "en-india-female": "en-IN-NeerjaNeural",
    "en-india-male": "en-IN-PrabhatNeural",
    "en-us-female": "en-US-AriaNeural",
    "en-us-male": "en-US-GuyNeural",
}


class VoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice: str = "hi-female"
    speed: int = Field(default=15, ge=-50, le=50)
    pitch: int = Field(default=4, ge=-10, le=10)


@app.get("/", response_class=HTMLResponse)
async def home():
    page = BASE_DIR / "index.html"
    if not page.exists():
        raise HTTPException(
            status_code=404,
            detail="index.html file nahi mili."
        )
    return page.read_text(encoding="utf-8")


@app.get("/api/voices")
async def get_voices():
    return {
        "voices": [
            {"id": "hi-female", "name": "Hindi Female — Swara"},
            {"id": "hi-male", "name": "Hindi Male — Madhur"},
            {"id": "en-india-female", "name": "Indian English Female — Neerja"},
            {"id": "en-india-male", "name": "Indian English Male — Prabhat"},
            {"id": "en-us-female", "name": "US English Female — Aria"},
            {"id": "en-us-male", "name": "US English Male — Guy"},
        ]
    }


@app.post("/api/generate")
async def generate_voice(request: VoiceRequest):
    text = request.text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Pehle kuch text likho."
        )

    if request.voice not in VOICES:
        raise HTTPException(
            status_code=400,
            detail="Voice option sahi nahi hai."
        )

    filename = f"rishi_{time.time_ns()}.mp3"
    output_path = AUDIO_DIR / filename

    try:
        speaker = edge_tts.Communicate(
            text=text,
            voice=VOICES[request.voice],
            rate=f"{request.speed:+d}%",
            pitch=f"{request.pitch:+d}Hz",
        )
        await speaker.save(str(output_path))

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Audio file nahi bani.")

        return {
            "success": True,
            "message": "Voice taiyar hai!",
            "filename": filename,
            "audio_url": f"/audio/{filename}",
            "download_url": f"/download/{filename}",
        }

    except Exception as error:
        if output_path.exists():
            output_path.unlink(missing_ok=True)

        print("Voice generation error:", repr(error))
        raise HTTPException(
            status_code=502,
            detail=(
                "Voice generate nahi ho paayi. Internet check karo "
                "aur dobara try karo."
            ),
        )


@app.get("/audio/{filename}")
async def play_audio(filename: str):
    if not re.fullmatch(r"rishi_[0-9]+\.mp3", filename):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    audio_path = AUDIO_DIR / filename

    if not audio_path.is_file():
        raise HTTPException(status_code=404, detail="Audio nahi mili.")

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=filename,
    )


@app.get("/download/{filename}")
async def download_audio(filename: str):
    if not re.fullmatch(r"rishi_[0-9]+\.mp3", filename):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    audio_path = AUDIO_DIR / filename

    if not audio_path.is_file():
        raise HTTPException(status_code=404, detail="Audio nahi mili.")

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )