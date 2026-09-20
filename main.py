import os
import secrets
import struct
import zlib
from functools import lru_cache

import fal_client
from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

HERE = os.path.dirname(os.path.abspath(__file__))

# Allowed fal.ai models (id -> label). Edit freely; see https://fal.ai/models
MODELS = {
    "fal-ai/minimax/video-01": "MiniMax Video-01 (fast, cheaper)",
    "fal-ai/kling-video/v2/master/text-to-video": "Kling 2.0 Master (higher quality)",
}

APP_PASSWORD = os.getenv("APP_PASSWORD", "")
app = FastAPI(title="Reelmaker")


def check_auth(pw):
    if not APP_PASSWORD:
        raise HTTPException(500, "Server has no APP_PASSWORD set.")
    if not secrets.compare_digest((pw or "").encode(), APP_PASSWORD.encode()):
        raise HTTPException(401, "Wrong access password.")


class GenerateIn(BaseModel):
    prompt: str
    model: str


@app.get("/api/models")
def models():
    return [{"id": k, "label": v} for k, v in MODELS.items()]


@app.post("/api/generate")
def generate(body: GenerateIn, x_app_password: str = Header(None)):
    check_auth(x_app_password)
    prompt = body.prompt.strip()
    if not prompt or len(prompt) > 1000:
        raise HTTPException(400, "Prompt must be 1-1000 characters.")
    if body.model not in MODELS:
        raise HTTPException(400, "Unknown model.")
    if not os.getenv("FAL_KEY"):
        raise HTTPException(500, "Server has no FAL_KEY set.")
    handle = fal_client.submit(body.model, arguments={"prompt": prompt})
    return {"id": handle.request_id}


@app.get("/api/status")
def status(model: str, rid: str, x_app_password: str = Header(None)):
    check_auth(x_app_password)
    if model not in MODELS:
        raise HTTPException(400, "Unknown model.")
    try:
        s = fal_client.status(model, rid)
        if isinstance(s, fal_client.Completed):
            result = fal_client.result(model, rid)
            return {"state": "done", "url": result["video"]["url"]}
        if isinstance(s, fal_client.Queued):
            return {"state": "queued", "position": s.position}
        return {"state": "running"}
    except Exception as e:
        return {"state": "error", "message": str(e)[:300]}


# ---- App shell: page, service worker, manifest, icons ----
@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "index.html"), media_type="text/html")


@app.get("/sw.js")
def sw():
    return FileResponse(os.path.join(HERE, "sw.js"), media_type="application/javascript")


@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse(
        {
            "name": "Reelmaker",
            "short_name": "Reelmaker",
            "description": "Turn a text prompt into an AI video.",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#EDF0F4",
            "theme_color": "#2A45F5",
            "icons": [
                {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            ],
        },
        media_type="application/manifest+json",
    )


@lru_cache(maxsize=None)
def make_icon(size: int) -> bytes:
    """Blue square with a white play triangle, generated in pure Python."""
    bg, fg = (42, 69, 245), (255, 255, 255)
    (x1, y1), (x2, y2), (x3, y3) = (0.39 * size, 0.30 * size), (0.39 * size, 0.70 * size), (0.72 * size, 0.50 * size)
    d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            px, py = x + 0.5, y + 0.5
            a = ((y2 - y3) * (px - x3) + (x3 - x2) * (py - y3)) / d
            b = ((y3 - y1) * (px - x3) + (x1 - x3) * (py - y3)) / d
            raw.extend(fg if (a >= 0 and b >= 0 and a + b <= 1) else bg)

    def chunk(t, data):
        c = struct.pack(">I", len(data)) + t + data
        return c + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


@app.get("/icon-192.png")
def icon192():
    return Response(make_icon(192), media_type="image/png")


@app.get("/icon-512.png")
def icon512():
    return Response(make_icon(512), media_type="image/png")
