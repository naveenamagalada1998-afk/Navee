import os
import secrets

import fal_client
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Allowed fal.ai models (id -> label). Edit freely; see https://fal.ai/models
MODELS = {
    "fal-ai/minimax/video-01": "MiniMax Video-01 (fast, cheaper)",
    "fal-ai/kling-video/v2/master/text-to-video": "Kling 2.0 Master (higher quality)",
}

APP_PASSWORD = os.getenv("APP_PASSWORD", "")
app = FastAPI(title="Reelmaker")


def check_auth(pw: str | None):
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
def generate(body: GenerateIn, x_app_password: str | None = Header(None)):
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
def status(model: str, rid: str, x_app_password: str | None = Header(None)):
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


