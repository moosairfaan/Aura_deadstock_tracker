"""
Vercel serverless entry: `vercel.json` builds this file; it re-exports `app` from `app.main`.

Run locally (from repo root — recommended for Render/Railway):
  uvicorn app.main:app --host 0.0.0.0 --port 8000

This file also works (re-exports the same app):
  uvicorn main:app --host 0.0.0.0 --port 8000

Production: Procfile / render.yaml use `app.main:app` so deploy works even when
`main.py` is not importable (e.g. Render root directory set to `app/`).
"""
from __future__ import annotations

import os

from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
