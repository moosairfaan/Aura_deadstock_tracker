#!/usr/bin/env python3
"""
Extract high-intent fashion keywords from raw Pinterest pin JSON.

Reads pin_description (pin.description), board_name (board_ref.name), and
pin.alt_text. Applies an inspo/fashion filter, scores longevity from board
spread + save-like engagement (reaction_counts), and writes pinterest_trends.json.

Use pinterest_aggregator_weight (1.3) when merging with TikTok/Instagram.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PINTEREST_AGGREGATOR_WEIGHT = 1.3
TOP_N = 15

DEFAULT_INPUT = Path(__file__).resolve().parent / "dataset_pinterest-scraper-search_2026-05-03_20-38-56-322.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "pinterest_trends.json"

# "Inspo" / style signals — pin must match at least one (or a garment term) to contribute.
STYLE_SIGNAL_RE = re.compile(
    r"aesthetic|outfit\s*ideas?|styling\s*tips?|inspo|inspiration|lookbook|"
    r"ootd|capsule\s*wardrobe|street\s*style|streetwear|fashion|chic|"
    r"vogue|runway|wardrobe|how\s*to\s*style|dressing|trendy|ensemble|"
    r"moodboard|closet|minimal\s*style|quiet\s*luxury|old\s*money|"
    r"elevated\s*basic|layering|seasonal\s*style|editorial",
    re.IGNORECASE,
)

GARMENT_OR_FASHION_RE = re.compile(
    r"\b(dress|dresses|skirt|blazer|denim|jeans|pants|trousers|chinos?|knit|sweater|"
    r"cardigan|coat|jacket|bomber|parka|heels|boots|sneakers|loafers|sandals|"
    r"handbag|bag|totes?|jewelry|jewellery|suit|shirt|blouse|top|tee|polo|"
    r"hoodie|cargo|vest|linen|silk|leather|tailoring|swimwear|lingerie|"
    r"activewear|basics|outerwear|knitwear|footwear|accessories|belt|scarf|"
    r"oversized|pleated|wide[\s-]?leg|slim\s*fit|tailored|formal|casual\s*wear)\b",
    re.IGNORECASE,
)

NOISE_KEYWORDS = frozenset(
    {
        "products",
        "product",
        "uploaded",
        "pinterest",
        "shop",
        "shopping",
        "cart",
        "sale",
        "item",
        "items",
        "length",
        "width",
        "height",
        "size",
        "available",
        "click",
        "link",
    }
)


STOPWORDS = frozenset(
    """
    the a an and or but in on at to for of as is was are were be been being
    with from by this that these those it its into over under up out if then
    than so not no yes all any some more most very just also only even can could
    will would should may might must about after before between through during
    your our their his her my me we you he she them us one two first last new
    old get got make made like just see seen way use used using per via com
    www http https pin img pinterest uploaded user man woman men women wearing
    background image photo picture standing walking sitting leaning against side
    building street car cars blurry trees ocean city mountains grass outdoor
    indoor front back left right near next holding wearing has have had having
    been being such same other another each every both few little much many
    """.split()
) | NOISE_KEYWORDS


def _gather_pin_text(record: dict[str, Any]) -> str:
    pin = record.get("pin") if isinstance(record.get("pin"), dict) else {}
    parts: list[str] = []
    for key in ("title", "description", "alt_text"):
        val = pin.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    rs = pin.get("rich_summary")
    if isinstance(rs, dict):
        for rk in ("display_name", "name", "description"):
            rv = rs.get(rk)
            if isinstance(rv, str) and rv.strip():
                parts.append(rv.strip())
    board = record.get("board_ref")
    if isinstance(board, dict):
        bn = board.get("name")
        if isinstance(bn, str) and bn.strip():
            parts.append(bn.strip())
    root_title = record.get("title")
    if isinstance(root_title, str) and root_title.strip():
        parts.append(root_title.strip())
    return " \n ".join(parts)


def _pin_passes_inspo_filter(text: str) -> bool:
    if len(text.strip()) < 10:
        return False
    return bool(STYLE_SIGNAL_RE.search(text) or GARMENT_OR_FASHION_RE.search(text))


def _reaction_save_proxy(pin: dict[str, Any]) -> int:
    rc = pin.get("reaction_counts")
    if not isinstance(rc, dict):
        return 0
    total = 0
    for v in rc.values():
        try:
            total += int(v)
        except (TypeError, ValueError):
            continue
    return max(0, total)


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[#@]+", " ", text)
    text = re.sub(r"[_/|]+", " ", text)
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text)
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def _phrases_from_tokens(tokens: list[str]) -> set[str]:
    """Bigrams, trigrams, and selective unigrams (garment / long descriptive tokens)."""
    out: set[str] = set()
    for i in range(len(tokens) - 1):
        a, b = tokens[i], tokens[i + 1]
        if len(a) > 2 and len(b) > 2:
            out.add(f"{a} {b}")
    for i in range(len(tokens) - 2):
        a, b, c = tokens[i], tokens[i + 1], tokens[i + 2]
        if min(len(a), len(b), len(c)) > 2:
            out.add(f"{a} {b} {c}")
    for w in tokens:
        if len(w) < 4:
            continue
        if GARMENT_OR_FASHION_RE.search(f" {w} ") or len(w) >= 6:
            out.add(w)
    return out


def _phrases_from_clauses(text: str) -> set[str]:
    """Comma / newline separated chunks (Pinterest descriptions, alt blobs)."""
    chunks = re.split(r"[\n\r,;]+", text)
    phrases: set[str] = set()
    for chunk in chunks:
        chunk = chunk.strip()
        if len(chunk) < 4:
            continue
        tokens = _tokenize(chunk)
        phrases |= _phrases_from_tokens(tokens)
    tokens = _tokenize(text)
    phrases |= _phrases_from_tokens(tokens)
    return phrases


def _normalize_keyword_display(kw: str) -> str:
    return " ".join(w if w.islower() else w.lower() for w in kw.split()).strip()


def aesthetic_from_pin_text(text: str) -> str | None:
    """Infer when board title is generic (Products, etc.)."""
    t = text.lower()
    if re.search(r"wedding|bridal|bride|groom|ceremony", t):
        return "Occasion Wear"
    if re.search(r"summer\s+wedding|beach\s+wedding|garden\s+wedding", t):
        return "Occasion Wear"
    if re.search(r"capsule|minimal\s+wardrobe|quiet\s+luxury", t):
        return "Capsule / Essentials"
    if re.search(r"streetwear|urban\s+outfit|skater", t):
        return "Streetwear"
    if re.search(r"y2k|90s\s+fashion|vintage\s+denim", t):
        return "Retro / Archive"
    if re.search(r"office\s+outfit|workwear|business\s+casual", t):
        return "Workwear"
    if re.search(r"resort|vacation\s+outfit|beach\s+outfit", t):
        return "Resort / Summer"
    return None


def aesthetic_from_board(board_name: str) -> str:
    n = board_name.lower()
    if re.search(r"wedding|bridal|bride|groom|ceremony|reception", n):
        return "Occasion Wear"
    if re.search(r"beach|resort|vacation|summer\s*vibes|pool", n):
        return "Resort / Summer"
    if re.search(r"fall|autumn|september|october|cozy|pumpkin", n):
        return "Autumn Mood"
    if re.search(r"winter|holiday|christmas|snow|cold\s*weather", n):
        return "Holiday / Winter"
    if re.search(r"streetwear|urban|skate|mens\s*style|men\s*outfit", n):
        return "Streetwear"
    if re.search(r"capsule|minimal|basics|essentials|uniform", n):
        return "Capsule / Essentials"
    if re.search(r"work|office|business|corporate|9\s*to\s*5", n):
        return "Workwear"
    if re.search(r"vintage|y2k|90s|80s|retro|archive|thrift", n):
        return "Retro / Archive"
    if re.search(r"spring|floral|garden\s*party|picnic", n):
        return "Spring / Romance"
    if re.search(r"party|night\s*out|club|cocktail|gala", n):
        return "Going Out"
    if re.search(r"home\s*decor|kitchen\b|recipe\b|\bdiy\b", n):
        return "Lifestyle Adjacent"
    if re.search(r"product|shop|buy|cart|wishlist", n):
        return "Shopping / Catalog"
    return "Editorial / General"


GENERIC_UNIGRAMS = frozenset(
    {
        "fashion",
        "outfit",
        "outfits",
        "clothing",
        "style",
        "aesthetic",
        "modern",
        "classic",
        "casual",
        "perfect",
        "comfort",
        "inspiration",
        "ideas",
        "trendy",
        "beautiful",
        "gorgeous",
        "stunning",
        "elegant",
        "design",
        "quality",
        "double",
        "sleeve",
    }
)


def _keyword_fashion_noise(kw: str) -> bool:
    """Drop obviously non-fashion phrases."""
    low = kw.lower()
    if len(low) < 4:
        return True
    first = low.split()[0] if low.split() else ""
    if first in NOISE_KEYWORDS or low in NOISE_KEYWORDS:
        return True
    if re.search(r"\b(man|woman|men|women)\s+(wearing|standing|leaning)\b", low):
        return True
    if re.search(r"\b(background|blurry|image|photo|picture)\b", low):
        return True
    parts = low.split()
    if len(parts) == 3 and parts[0] == parts[2]:
        return True
    if len(parts) >= 2 and len(set(parts)) == 1:
        return True
    if "amazon" in low or "influencer" in low:
        return True
    if re.search(r"\b(affiliate|sponsored|discount\s*code|promo\s*code)\b", low):
        return True
    return False


def longevity_score(unique_boards: int, pin_hits: int, save_proxy: int) -> float:
    """
    Higher when a keyword appears across many boards (cross-board persistence)
    and when underlying pins show stronger reaction/save-like engagement.
    """
    b = max(0, unique_boards)
    p = max(0, pin_hits)
    s = max(0, save_proxy)
    raw = 6.2 * b + 2.2 * math.log1p(s) + 1.6 * math.log1p(p)
    return round(min(100.0, raw), 2)


def _ranking_score(longevity: float, keyword_display: str) -> float:
    """Prefer multi-word 'visual vocabulary' phrases; downrank ultra-generic unigrams."""
    parts = keyword_display.split()
    phrase_boost = 1.0 + 0.55 * (len(parts) - 1) if len(parts) > 1 else 1.0
    if len(parts) == 1 and parts[0].lower() in GENERIC_UNIGRAMS:
        phrase_boost *= 0.38
    return longevity * phrase_boost


def process_pins(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Per keyword aggregate:
    - boards: set of board ids
    - pin_ids
    - save_sum (reaction proxy)
    - aesthetic votes from board names
    """
    agg: dict[str, dict[str, Any]] = {}

    for rec in records:
        if not isinstance(rec, dict):
            continue
        if str(rec.get("type") or rec.get("entity_type") or "").lower() != "pin":
            continue
        text = _gather_pin_text(rec)
        if not _pin_passes_inspo_filter(text):
            continue
        pin = rec.get("pin")
        if not isinstance(pin, dict):
            continue
        board_ref = rec.get("board_ref")
        board_id = str(board_ref.get("id", "")) if isinstance(board_ref, dict) else ""
        board_name = str(board_ref.get("name", "")) if isinstance(board_ref, dict) else ""
        pin_id = str(rec.get("id", ""))
        saves = _reaction_save_proxy(pin)
        board_aesthetic = aesthetic_from_board(board_name)
        text_aesthetic = aesthetic_from_pin_text(text)
        aesthetic = text_aesthetic or board_aesthetic

        phrases = _phrases_from_clauses(text)
        for kw in phrases:
            disp = _normalize_keyword_display(kw)
            if len(disp) < 4 or _keyword_fashion_noise(disp):
                continue
            key = disp.lower()
            if key not in agg:
                agg[key] = {
                    "display": disp,
                    "boards": set(),
                    "pins": set(),
                    "save_sum": 0,
                    "aesthetic_votes": Counter(),
                }
            slot = agg[key]
            if board_id:
                slot["boards"].add(board_id)
            if pin_id:
                slot["pins"].add(pin_id)
            slot["save_sum"] += saves
            slot["aesthetic_votes"][aesthetic] += 1 + int(math.log1p(saves))

    ranked: list[tuple[float, float, str]] = []
    for key, slot in agg.items():
        ub = len(slot["boards"])
        ph = len(slot["pins"])
        sv = int(slot["save_sum"])
        longevity = longevity_score(ub, ph, sv)
        display = slot["display"]
        rank = _ranking_score(longevity, display)
        ranked.append((rank, longevity, key))

    ranked.sort(key=lambda t: (-t[0], -t[1], t[2]))
    out_rows: list[dict[str, Any]] = []
    for _rank, longevity, key in ranked[:TOP_N]:
        slot = agg[key]
        aesthetic, _votes = slot["aesthetic_votes"].most_common(1)[0]
        if aesthetic == "Lifestyle Adjacent":
            alt = [(a, v) for a, v in slot["aesthetic_votes"].items() if a != "Lifestyle Adjacent"]
            if alt:
                aesthetic = max(alt, key=lambda x: x[1])[0]

        out_rows.append(
            {
                "keyword": slot["display"],
                "longevity_score": longevity,
                "source_aesthetic": aesthetic,
                "unique_boards": len(slot["boards"]),
                "pin_mentions": len(slot["pins"]),
                "weighted_save_proxy": int(slot["save_sum"]),
            }
        )
    return out_rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Build pinterest_trends.json from Pinterest pin export.")
    ap.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to Pinterest JSON export",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON path",
    )
    args = ap.parse_args()
    path: Path = args.input
    if not path.is_file():
        raise SystemExit(f"Input not found: {path}")

    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise SystemExit("Expected top-level JSON array of records")

    top_keywords = process_pins(data)
    payload = {
        "schema_version": 1,
        "source": "pinterest",
        "pinterest_aggregator_weight": PINTEREST_AGGREGATOR_WEIGHT,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "input_file": path.name,
        "top_keywords": top_keywords,
    }
    out: Path = args.output
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(top_keywords)} keywords to {out}")


if __name__ == "__main__":
    main()
