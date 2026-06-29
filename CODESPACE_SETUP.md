# Codespace Setup — Dev Backend for Vercel

Run the entire FastAPI + Playwright backend in a free GitHub cloud VM.
No load on your local machine.

## 1. Launch Codespace

1. Go to https://github.com/Nawaz-khan-droid/seo-autopilot
2. Click green **`<> Code`** → **Codespaces** tab → **Create codespace on main**
3. Wait ~60s for the VM to boot (VS Code opens in your browser)

## 2. Pull Latest Code

```bash
git pull origin main
```

## 3. Install Dependencies

In the Codespace terminal:

```bash
pip install -r requirements.txt
python -m playwright install chromium --with-deps
```

## 4. Set Environment Variables

```bash
cp .env.example .env
```

Then open `.env` and paste your keys:

```
GROQ_API_KEY=gsk_...          # Required
SERPAPI_KEY=                  # Optional — rank tracking
APIFY_API_KEY=                # Optional — SERP fallback
SEARCHAPI_API_KEY=            # Optional — SERP fallback
PAGESPEED_API_KEY=            # Optional — PSI rate limit increase
```

> **Never commit `.env`** — it is already in `.gitignore` and `.dockerignore`.

## 5. Start the Server

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## 6. Expose Public URL

When the server starts, VS Code shows a popup:
**"Your application running on port 8000 is available."**

- Click **Make Public**
- Copy the URL: `https://some-name-8000.preview.app.github.dev`

This URL is **HTTPS** and publicly accessible. No Cloudflare needed.

## 7. Connect Vercel Frontend

Point your Vercel frontend's API base URL to the Codespace URL above.

## 8. Run Tests (Optional)

```bash
GROQ_API_KEY=$(grep ^GROQ_API_KEY .env | cut -d= -f2) python -m pytest -v
```

## What This Codespace Runs

This Codespace runs **only the backend (FastAPI + Playwright)** — the API server that handles audit requests, crawls sites, generates DOCX reports, and serves data to the frontend.

It does **NOT** host the frontend (SPA). The frontend is deployed separately on Vercel and makes API calls to this Codespace's public URL.

## Keep It Alive

- Codespaces auto-sleeps after **30 minutes idle**
- Wakes in **~10 seconds** when you revisit the URL or open VS Code
- Free tier includes **60 hours/month** of 2-core / 4GB RAM compute
- To prevent sleep during active use: keep the terminal tab open or use a [keep-alive script](https://gist.github.com/curran/9b1fd62966db7d0978c8d411dd294bbc)
- All git operations work natively (Linux, no libcurl-4.dll issue)
