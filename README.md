# Reelmaker – text-to-video app (installable on your phone)

Python (FastAPI) backend + installable web app (PWA). Your fal.ai key stays on the server; the app is protected by a password so nobody else can spend your credits.

## 1. Get your keys
- fal.ai API key: https://fal.ai/dashboard/keys (add a few dollars of credit)
- Pick any APP_PASSWORD you like (this is what you type in the app once)

## 2. Test on your computer
    pip install -r requirements.txt
    export FAL_KEY=your_fal_key          # Windows: set FAL_KEY=your_fal_key
    export APP_PASSWORD=choose_a_password
    uvicorn main:app --port 8000
Open http://localhost:8000

## 3. Put it online (needed to install on your phone – free, HTTPS)
1. Upload this folder to a new private GitHub repo.
2. On https://render.com: New > Blueprint > pick the repo (it reads render.yaml).
3. Enter FAL_KEY and APP_PASSWORD when asked. Deploy.
4. You get a URL like https://reelmaker-xxxx.onrender.com
Note: the free plan sleeps after ~15 min idle; the first open takes ~30-60 s to wake.

Quick alternative without hosting: run step 2, then `cloudflared tunnel --url http://localhost:8000` to get a temporary HTTPS link (works only while your PC is on).

## 4. Install on your phone
- Android (Chrome): open the URL > menu (⋮) > "Install app" / "Add to Home screen".
- iPhone (Safari): Share > "Add to Home Screen".
Open it from the home screen, enter your password once, and generate.

## Notes
- Each video costs money on fal.ai (pricing per model on fal.ai/models). Start with MiniMax.
- Add or change models in MODELS at the top of main.py (use the exact fal.ai endpoint ID).
- Video links come from fal.ai and may expire; download videos you want to keep.
