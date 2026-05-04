#!/usr/bin/env python3
"""
Upload articles.csv and omni_trends.json to a public URL for Vercel serverless.

Options:
  1) Presigned PUT (S3 / R2 / Supabase): set env and run with --put
  2) GitHub raw: commit files to a public repo and paste raw URLs into Vercel env (no upload script needed)

Examples:
  python upload_data.py --print-env-hints
  python upload_data.py --articles articles_slim.csv --omni omni_trends.json --put

Env for --put (optional, any one provider you use):
  PRESIGNED_PUT_ARTICLES_URL   HTTP PUT target for CSV bytes
  PRESIGNED_PUT_OMNI_URL       HTTP PUT target for JSON bytes
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.request
from pathlib import Path


def _put_bytes(url: str, body: bytes, content_type: str | None) -> None:
    req = urllib.request.Request(url, data=body, method="PUT")
    if content_type:
        req.add_header("Content-Type", content_type)
    with urllib.request.urlopen(req, timeout=300) as resp:
        if resp.status not in (200, 201, 204):
            raise RuntimeError(f"Unexpected status {resp.status}")


def main() -> int:
    p = argparse.ArgumentParser(description="Upload or document hosting for remote CSV/JSON URLs.")
    p.add_argument("--articles", type=Path, default=Path("articles_slim.csv"), help="Local CSV path")
    p.add_argument("--omni", type=Path, default=Path("omni_trends.json"), help="Local omni trends JSON")
    p.add_argument("--put", action="store_true", help="PUT files using presigned URLs from env")
    p.add_argument("--print-env-hints", action="store_true", help="Print Vercel env vars + GitHub raw instructions")
    args = p.parse_args()

    if args.print_env_hints:
        print(
            """
=== Vercel environment variables ===
Set these on your Vercel project (Settings → Environment Variables):

  ARTICLES_CSV_URL=https://.../articles_slim.csv
  OMNI_TRENDS_URL=https://.../omni_trends.json

=== GitHub Raw (no upload script) ===
1. Put articles_slim.csv and omni_trends.json in a public GitHub repo (or a dedicated data branch).
2. Use raw URLs, for example:
   https://raw.githubusercontent.com/<user>/<repo>/<branch>/articles_slim.csv
   https://raw.githubusercontent.com/<user>/<repo>/<branch>/omni_trends.json
3. Paste those into ARTICLES_CSV_URL and OMNI_TRENDS_URL.

=== Presigned PUT (S3 / Cloudflare R2 / etc.) ===
Create two presigned PUT URLs that accept application/octet-stream, then export:

  export PRESIGNED_PUT_ARTICLES_URL='https://...'
  export PRESIGNED_PUT_OMNI_URL='https://...'
  python upload_data.py --articles path/to.csv --omni path/to.json --put

Files must be publicly readable over HTTPS for the FastAPI function to fetch them (unless you use signed GET + pass secrets, not implemented here).
"""
        )
        return 0

    if not args.put:
        print("Tip: set ARTICLES_CSV_URL + OMNI_TRENDS_URL on Vercel, or run with --print-env-hints\n")

    if not args.articles.is_file():
        print(f"Missing articles file: {args.articles}", file=sys.stderr)
        return 1
    if not args.omni.is_file():
        print(f"Missing omni file: {args.omni}", file=sys.stderr)
        return 1

    a_url = os.getenv("PRESIGNED_PUT_ARTICLES_URL", "").strip()
    o_url = os.getenv("PRESIGNED_PUT_OMNI_URL", "").strip()

    if args.put:
        if not a_url or not o_url:
            print("Set PRESIGNED_PUT_ARTICLES_URL and PRESIGNED_PUT_OMNI_URL for --put.", file=sys.stderr)
            return 1
        csv_bytes = args.articles.read_bytes()
        json_bytes = args.omni.read_bytes()
        print(f"PUT {len(csv_bytes)} bytes → articles …")
        _put_bytes(a_url, csv_bytes, "text/csv")
        print(f"PUT {len(json_bytes)} bytes → omni …")
        _put_bytes(o_url, json_bytes, "application/json")
        print("Done. Point ARTICLES_CSV_URL / OMNI_TRENDS_URL at the public GET URLs for those objects.")
        return 0

    print(f"articles: {args.articles} ({args.articles.stat().st_size} bytes)")
    print(f"omni:     {args.omni} ({args.omni.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
