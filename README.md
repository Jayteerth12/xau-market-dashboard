# XAU Market Dashboard

A tiny, two-service copy of the Market Environment dashboard: classifies the
current market regime (trend / range / compression / choppy) for any OANDA
instrument and scores which trading setups currently fit it. Does not
predict direction, place trades, or store any data.

- **`backend/`** — a small stateless FastAPI service (live OANDA data only,
  no database, no historical replay, no paper trading). Deploy to
  [Railway](https://railway.app) (or Render/Fly.io — anything that runs a
  Python web process on its free tier).
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
through git. They only get entered again, directly, on Railway.

## 3. Deploy the backend to Railway

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub repo → select `xau-market-dashboard`.
2. In the service settings, set **Root Directory** to `backend`.
3. Railway auto-detects the `Procfile` and Python via Nixpacks — no extra build config needed.
4. Add environment variables (Settings → Variables): `OANDA_TOKEN`, `OANDA_ACCOUNT_ID`, `OANDA_ENVIRONMENT` (same values as your local `.env`).
5. Deploy. Once it's up, note the public URL Railway gives you (`https://<something>.up.railway.app`) and confirm `https://<that-url>/health` returns `{"status": "running"}`.

Railway's free tier sleeps/limits usage after a monthly credit runs out —
fine for a personal demo; check their current free-tier terms if this needs
to stay up continuously.

## 4. Deploy the frontend to Vercel

1. [vercel.com](https://vercel.com) → Add New → Project → import `xau-market-dashboard`.
2. Set **Root Directory** to `frontend`. Framework preset: "Other" (it's static — no build command, no install command needed).
3. Deploy. Open the resulting `*.vercel.app` URL.
4. Paste your Railway backend URL into the "API base URL" field and click Save — this is stored in the browser's `localStorage`, not in the deployed code, so you (or anyone) can point the same frontend at a different backend later with no redeploy.

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
