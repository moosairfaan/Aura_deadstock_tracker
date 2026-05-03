#!/usr/bin/env python3
"""
Drop columns from articles.csv that the FastAPI app never reads.

app/main.py only uses: article_id, product_code, prod_name, product_type_name, detail_desc

Usage:
  python scripts/slim_articles_csv.py
  python scripts/slim_articles_csv.py -i articles.csv -o articles_slim.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# Must match app/main.py _build_description + MatchedProduct fields
KEEP = ["article_id", "product_code", "prod_name", "product_type_name", "detail_desc"]

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser(description="Slim articles CSV to columns used by the API.")
    ap.add_argument("-i", "--input", type=Path, default=ROOT / "articles.csv")
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "articles_slim.csv")
    args = ap.parse_args()
    inp: Path = args.input
    out: Path = args.output
    if not inp.is_file():
        raise SystemExit(f"Input not found: {inp}")

    df = pd.read_csv(inp, dtype=str, low_memory=False)
    missing = [c for c in KEEP if c not in df.columns]
    if missing:
        raise SystemExit(f"Input missing required columns {missing}; have: {list(df.columns)}")

    slim = df[KEEP].copy()
    # Drop rows with no article_id (same filter as API startup)
    slim = slim[slim["article_id"].astype(str).str.strip() != ""]

    before = inp.stat().st_size
    slim.to_csv(out, index=False, encoding="utf-8")
    after = out.stat().st_size
    pct = 100.0 * (1.0 - after / max(before, 1))
    print(f"Rows: {len(slim):,}  Columns: {len(KEEP)}")
    print(f"Size: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB (~{pct:.0f}% smaller)")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
