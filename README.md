# XAU Market Dashboard

A tiny, two-service copy of the Market Environment dashboard: classifies the
current market regime (trend / range / compression / choppy) for any OANDA
instrument and scores which trading setups currently fit it. Does not
predict direction, place trades, or store any data.

- **`backend/`** — a small stateless FastAPI service (live OANDA data only,
  no database, no historical replay, no paper trading). Deploy to
  [Render](https://render.com)'s free tier (or Fly.io/PythonAnywhere —
  anything that runs a Python web process for free).
- **`frontend/`** — a static HTML/CSS/JS page (no build step, no framework)
  that calls the backend. Deploy to [Vercel](https://vercel.com).

## 1. Run locally first

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your OANDA credentials
python smoke_test.py   # one end-to-end check against live OANDA data
uvicorn main:app --reload
```

In another terminal:

```bash
cd frontend
python3 -m http.server 5500
```

Open `http://localhost:5500`, paste `http://localhost:8000` (or whatever
port uvicorn used) into the "API base URL" box, click Save, then Analyze.

## 2. Push to GitHub

```bash
cd /Users/jayteertha/xau-market-dashboard
git init
git add .
git commit -m "Initial commit: XAU market dashboard (frontend + backend)"
```

Then either:

```bash
# with GitHub CLI (gh auth login first, one-time)
gh repo create xau-market-dashboard --public --source=. --remote=origin --push
```

or via the GitHub web UI ("New repository" → don't initialize with a
README → then):

```bash
git remote add origin https://github.com/<your-username>/xau-market-dashboard.git
git branch -M main
git push -u origin main
```

`.env` is gitignored — your OANDA credentials never leave your machine
through git. They only get entered again, directly, on Render.

## 3. Deploy the backend to Render

Easiest path — Blueprint (reads `render.yaml` at the repo root, auto-configures everything):

1. [dashboard.render.com](https://dashboard.render.com) → New → Blueprint → connect the `xau-market-dashboard` repo.
2. Render reads `render.yaml` and proposes one service (`xau-market-dashboard-api`, root dir `backend`, free plan). Confirm.
3. It'll prompt for the two secret env vars marked `sync: false` in the blueprint: `OANDA_TOKEN` and `OANDA_ACCOUNT_ID` (same values as your local `.env`). `OANDA_ENVIRONMENT` is already set to `practice`.
4. Deploy. Once it's up, note the public URL Render gives you (`https://xau-market-dashboard-api.onrender.com`) and confirm `https://<that-url>/health` returns `{"status": "running"}`.

(Manual alternative, no blueprint: New → Web Service → connect repo → Root Directory `backend` → Runtime `Python 3` → Build Command `pip install -r requirements.txt` → Start Command `uvicorn main:app --host 0.0.0.0 --port $PORT` → add the same env vars → free plan.)

Render's free tier is free indefinitely, but the service spins down after
~15 minutes idle and takes 30-60s to wake back up on the next request —
fine for a personal demo; the frontend will just show "Loading..." a bit
longer on the first request after a while.

## 4. Deploy the frontend to Vercel

1. [vercel.com](https://vercel.com) → Add New → Project → import `xau-market-dashboard`.
2. Set **Root Directory** to `frontend`. Framework preset: "Other" (it's static — no build command, no install command needed).
3. Deploy. Open the resulting `*.vercel.app` URL.
4. Paste your Render backend URL into the "API base URL" field and click Save — this is stored in the browser's `localStorage`, not in the deployed code, so you (or anyone) can point the same frontend at a different backend later with no redeploy.

## Notes

- The backend is public and read-only by design (`allow_origins=["*"]` —
  there's no user data or trading action behind this API, only market
  classification, so open CORS is intentionally simple here).
- This is a deliberately smaller slice of the full dashboard: **live mode
  only**, Market Environment tab only. No historical replay (needs a ~150MB
  dataset), no paper trading (that stays in the main private trading stack).
- `backend/regime_engine/` is a trimmed, standalone copy of the regime/setup
  logic from the main `xau-trading-stack` project — kept in sync manually,
  not imported as a shared package, so this repo can be deployed completely
  independently.
