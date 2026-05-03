#!/usr/bin/env python3
"""
Merge TikTok, Instagram, Pinterest (optional Google) trend JSON into omni_trends.json.

Weights: Google 1.0, TikTok 1.5, Instagram 1.2, Pinterest 1.3
Semantic clusters map aliases (e.g. Old Money + Quiet Luxury) to one Power Trend label.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Per-source multipliers for normalized [0,1] strength
WEIGHTS: dict[str, float] = {
    "google": 1.0,
    "tiktok": 1.5,
    "instagram": 1.2,
    "pinterest": 1.3,
}

ROOT = Path(__file__).resolve().parent

DEFAULT_PATHS: dict[str, Path] = {
    "tiktok": ROOT / "tiktok_trends.json",
    "instagram": ROOT / "instagram_trends.json",
    "pinterest": ROOT / "pinterest_trends.json",
    "google": ROOT / "google_trends.json",
}

# (power_trend_display, aliases) — match by normalized compact key (letters+digits only)
POWER_CLUSTERS: list[tuple[str, frozenset[str]]] = [
    (
        "Quiet Luxury",
        frozenset(
            {
                "quiet luxury",
                "quietluxury",
                "old money",
                "oldmoney",
                "stealth wealth",
                "stealthwealth",
                "old money aesthetic",
                "quiet luxury aesthetic",
                "lvmh quiet luxury",
                "stealth wealth aesthetic",
            }
        ),
    ),
    (
        "Clean Girl",
        frozenset(
            {
                "clean girl",
                "cleangirl",
                "clean girl aesthetic",
                "that girl aesthetic",
                "minimal makeup look",
            }
        ),
    ),
    (
        "Coastal / Resort",
        frozenset(
            {
                "coastal granddaughter",
                "coastal grandmother",
                "resort wear",
                "resortwear",
                "beach outfit",
                "vacation outfit",
            }
        ),
    ),
    (
        "Streetwear Core",
        frozenset(
            {
                "streetwear",
                "street style",
                "streetstyle",
                "urban outfit",
                "mens streetwear",
            }
        ),
    ),
    (
        "Capsule Wardrobe",
        frozenset(
            {
                "capsule wardrobe",
                "capsulewardrobe",
                "minimal wardrobe",
                "uniform dressing",
            }
        ),
    ),
]


def _norm_compact(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _resolve_power_trend(raw_keyword: str) -> tuple[str, str]:
    """
    Returns (merge_key, display_keyword).
    merge_key is lower display for stable dedupe; display is human-facing (Power Trend or title case raw).
    """
    raw = (raw_keyword or "").strip()
    if not raw:
        return "", ""
    nk = _norm_compact(raw)
    for display, aliases in POWER_CLUSTERS:
        for a in aliases:
            if _norm_compact(a) == nk:
                return display.lower(), display
    key = " ".join(raw.lower().split())
    disp = " ".join(w[:1].upper() + w[1:].lower() if w else "" for w in raw.split())
    return key, disp


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _normalize_list(items: list[dict[str, Any]], score_key: str) -> list[dict[str, Any]]:
    vals = [float(x.get(score_key) or 0.0) for x in items]
    m = max(vals) if vals else 1.0
    if m <= 0:
        m = 1.0
    out = []
    for x in items:
        y = dict(x)
        y["_norm"] = max(0.0, min(1.0, float(x.get(score_key) or 0.0) / m))
        out.append(y)
    return out


def _load_tiktok(path: Path) -> list[tuple[str, float, str]]:
    data = _read_json(path)
    if not data:
        return []
    items = data.get("top_keywords")
    if not isinstance(items, list):
        return []
    items = _normalize_list([x for x in items if isinstance(x, dict)], "virality_score")
    out: list[tuple[str, float, str]] = []
    for row in items:
        kw = str(row.get("keyword", "")).strip()
        if not kw:
            continue
        mk, disp = _resolve_power_trend(kw)
        out.append((mk, float(row["_norm"]) * WEIGHTS["tiktok"], disp))
    return out


def _load_instagram(path: Path) -> list[tuple[str, float, str]]:
    data = _read_json(path)
    if not data:
        return []
    items = data.get("top_keywords")
    if not isinstance(items, list):
        return []
    items = _normalize_list([x for x in items if isinstance(x, dict)], "influence_score")
    out: list[tuple[str, float, str]] = []
    for row in items:
        kw = str(row.get("keyword", "")).strip()
        if not kw:
            continue
        mk, disp = _resolve_power_trend(kw)
        out.append((mk, float(row["_norm"]) * WEIGHTS["instagram"], disp))
    return out


def _load_pinterest(path: Path) -> list[tuple[str, float, str]]:
    data = _read_json(path)
    if not data:
        return []
    items = data.get("top_keywords")
    if not isinstance(items, list):
        return []
    items = _normalize_list([x for x in items if isinstance(x, dict)], "longevity_score")
    out: list[tuple[str, float, str]] = []
    for row in items:
        kw = str(row.get("keyword", "")).strip()
        if not kw:
            continue
        mk, disp = _resolve_power_trend(kw)
        out.append((mk, float(row["_norm"]) * WEIGHTS["pinterest"], disp))
    return out


def _load_google(path: Path) -> list[tuple[str, float, str]]:
    """
    Optional google_trends.json:
      { "top_keywords": [ { "keyword": "...", "rising_score": 8.2 } ] }
    or "interest_score" / "score".
    """
    data = _read_json(path)
    if not data:
        return []
    items = data.get("top_keywords")
    if not isinstance(items, list):
        return []
    rows = [x for x in items if isinstance(x, dict)]
    key = None
    for candidate in ("rising_score", "interest_score", "score", "weight"):
        if rows and candidate in rows[0]:
            key = candidate
            break
    if not key:
        return []
    items = _normalize_list(rows, key)
    out: list[tuple[str, float, str]] = []
    for row in items:
        kw = str(row.get("keyword", "")).strip()
        if not kw:
            continue
        mk, disp = _resolve_power_trend(kw)
        out.append((mk, float(row["_norm"]) * WEIGHTS["google"], disp))
    return out


def aggregate(
    tiktok: list[tuple[str, float, str]],
    instagram: list[tuple[str, float, str]],
    pinterest: list[tuple[str, float, str]],
    google: list[tuple[str, float, str]],
) -> list[dict[str, Any]]:
    # merge_key -> { display, sources{src: sum} }
    bucket: dict[str, dict[str, Any]] = {}

    def feed(rows: list[tuple[str, float, str]], src: str) -> None:
        for merge_key, weighted, display in rows:
            if not merge_key:
                continue
            if merge_key not in bucket:
                bucket[merge_key] = {"sources": defaultdict(float), "displays": Counter()}
            bucket[merge_key]["sources"][src] += weighted
            bucket[merge_key]["displays"][display] += weighted

    feed(tiktok, "tiktok")
    feed(instagram, "instagram")
    feed(pinterest, "pinterest")
    feed(google, "google")

    out: list[dict[str, Any]] = []
    for mk, data in bucket.items():
        srcs = {k: round(float(v), 4) for k, v in data["sources"].items() if v > 0}
        if not srcs:
            continue
        display = data["displays"].most_common(1)[0][0]
        merged = round(sum(srcs.values()), 4)
        row: dict[str, Any] = {
            "keyword": display,
            "merged_score": merged,
            "source_count": len(srcs),
            "sources": srcs,
        }
        power_labels = {pt for pt, _ in POWER_CLUSTERS}
        if display in power_labels:
            row["power_trend"] = display
        out.append(row)

    out.sort(key=lambda r: (-float(r["merged_score"]), r["keyword"].lower()))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Build omni_trends.json from platform trend files.")
    ap.add_argument("--tiktok", type=Path, default=DEFAULT_PATHS["tiktok"])
    ap.add_argument("--instagram", type=Path, default=DEFAULT_PATHS["instagram"])
    ap.add_argument("--pinterest", type=Path, default=DEFAULT_PATHS["pinterest"])
    ap.add_argument("--google", type=Path, default=DEFAULT_PATHS["google"])
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "omni_trends.json")
    args = ap.parse_args()

    tt = _load_tiktok(args.tiktok)
    ig = _load_instagram(args.instagram)
    pin = _load_pinterest(args.pinterest)
    gg = _load_google(args.google)

    top_keywords = aggregate(tt, ig, pin, gg)
    payload = {
        "schema_version": 1,
        "sources": {
            "tiktok": args.tiktok.name,
            "instagram": args.instagram.name,
            "pinterest": args.pinterest.name,
            **({"google": args.google.name} if gg else {}),
        },
        "aggregator_weights": WEIGHTS,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "top_keywords": top_keywords,
    }
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(top_keywords)} merged keywords to {args.output}")


if __name__ == "__main__":
    main()
