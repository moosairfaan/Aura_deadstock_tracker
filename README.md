# Aura — Fashion relevance & production viability

Monorepo for a **FastAPI** backend (TF‑IDF search over a product catalog, trend-aware viability scoring) and a **Vite + React** dashboard. The API is designed to run on small serverless or container instances: **no PyTorch** in the default dependency set.

## What’s in the repo

| Path | Role |
|------|------|
| `app/main.py` | FastAPI app: `GET /`, `GET /health`, `POST /api/viability`, `GET /relevant-products` |
| `main.py` | Thin entry re-exporting `app` (used by Vercel’s `vercel.json`) |
| `dashboard/` | React + TypeScript + Tailwind + Vite |
| `requirements.txt` | Slim API dependencies (FastAPI, scikit-learn, pandas, httpx, …) |
| `render.yaml` | Optional [Render](https://render.com) Blueprint for the API |
| `upload_data.py` | Helper to document / push catalog + omni-trend files to public URLs (for serverless) |
| `scripts/slim_articles_csv.py` | Optional: reduce `articles.csv` to columns the API needs |

## How it works (API)

- **Catalog**: product rows are turned into text from name, description, and product type; **TF‑IDF** + cosine similarity (via scikit-learn) power relevance and match counts.
- **Omni trends** (optional): JSON with `top_keywords` and per-keyword scores is loaded to blend demand vs. catalog overlap in `/api/viability`.
- **Runtime data** (recommended for Vercel / small bundles): set **HTTPS URLs** so the function fetches data at cold start instead of shipping multi‑GB CSV/JSON in the deploy bundle:
  - `ARTICLES_CSV_URL` — CSV (must include `article_id` and `detail_desc`)
  - `OMNI_TRENDS_URL` — optional omni JSON
- **Local dev** can use `ARTICLES_CSV` / `OMNI_TRENDS_PATH` or the default files next to the repo root.

## Local development

**1. API (from repository root)**

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**2. Dashboard**

```bash
cd dashboard && npm install && npm run dev
```

Or from root: `npm run dev` — Vite runs on port **5173** and proxies **`/api`** to **`http://127.0.0.1:8000`**.

**3. Pointing the UI at a hosted API**

For production builds, set:

```bash
# dashboard/.env.local (do not commit secrets)
VITE_API_URL=https://your-api-host.example.com
```

Leave unset locally so the dev server keeps using the `/api` proxy.

## Environment variables (API)

| Variable | Purpose |
|----------|---------|
| `ARTICLES_CSV_URL` | HTTPS URL to CSV (production / serverless) |
| `OMNI_TRENDS_URL` | HTTPS URL to omni trends JSON |
| `ARTICLES_CSV` | Local path override when not using URL |
| `OMNI_TRENDS_PATH` | Local path for omni JSON |
| `SERPER_API_KEY` | Optional: live fashion trends via Serper |
| `SHOP_PRODUCT_URL_TEMPLATE` | Optional: `{article_id}`, `{product_code}`, `{prod_name}` for product links |
| `TFIDF_MAX_FEATURES` | Optional cap on vocabulary size (default `50000`) |

See `upload_data.py --print-env-hints` for hosting CSV/JSON on GitHub Raw or presigned PUT uploads.

## Deployment

**FastAPI**

- **Render**: connect the repo and use `render.yaml`, or set **Start command** to  
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
  with **root directory** left empty (repository root). Build: `pip install -r requirements.txt`.
- **Railway / Fly / Docker**: use `Procfile` (`gunicorn` + `app.main:app`) or the same `uvicorn` command with `$PORT`.
- **Vercel (Python serverless)**: `vercel.json` builds `main.py`; keep bundle small with `.vercelignore` and remote URLs for data. Use **`TFIDF_MAX_FEATURES`** and sized‑down CSVs if cold starts hit timeouts.

**Dashboard**

- Deploy **`dashboard/`** as a static/Vite site on Vercel or similar.
- Set **`VITE_API_URL`** to your deployed API origin and enable CORS on the API if origins differ (the API ships with permissive CORS for getting started).

## Project scripts

```bash
npm run dev       # Vite dev server (dashboard)
npm run build     # Production build → dashboard/dist
python upload_data.py --print-env-hints
```

## License

Add a license file if you intend open-source distribution (this repo does not include one by default).
