"""
Fashion articles API: rank products by semantic similarity to trending keywords.
"""
from __future__ import annotations

import os
import json
from urllib.parse import quote
from contextlib import asynccontextmanager
from collections import Counter
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

# Default relative to this package; override with ARTICLES_CSV
DEFAULT_CSV = Path(__file__).resolve().parent.parent / "articles.csv"
DEFAULT_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
TOP_K = 10
BATCH_SIZE = 256
SERPER_TRENDS_URL = "https://google.serper.dev/trends"
FASHION_SEED_KEYWORDS = ["Polka Dots", "Lace Skirt", "Jelly Flats", "Capris", "Brut Denim"]
APIFY_DATASET_FALLBACK = Path(__file__).resolve().parent.parent / "dataset_testing_2026-05-03_16-53-08-752.json"
OMNI_TRENDS_FALLBACK = Path(__file__).resolve().parent.parent / "omni_trends.json"
FASHION_HINTS = (
    "fashion",
    "style",
    "outfit",
    "streetwear",
    "runway",
    "wear",
    "dress",
    "skirt",
    "lace",
    "polka",
    "denim",
    "jeans",
    "jelly",
    "flat",
    "capri",
    "crochet",
    "swimwear",
    "accessories",
    "shoe",
    "shoes",
    "boots",
    "tops",
)


def _load_env_var_from_dotenv(key: str, dotenv_path: str = ".env") -> str | None:
    try:
        with open(dotenv_path, "r", encoding="utf-8") as fp:
            for raw_line in fp:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                lhs, rhs = line.split("=", 1)
                if lhs.strip() != key:
                    continue
                value = rhs.strip().strip("'").strip('"')
                return value or None
    except FileNotFoundError:
        return None
    return None


def _parse_percentage(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if not text:
        return None
    if "breakout" in text:
        return 10_000.0
    cleaned = text.replace("%", "").replace("+", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_interest_points(section: object) -> list[float]:
    points: list[float] = []
    if isinstance(section, list):
        for item in section:
            points.extend(_extract_interest_points(item))
    elif isinstance(section, dict):
        for key in ("value", "interest", "score"):
            val = section.get(key)
            parsed = _parse_percentage(val)
            if parsed is not None:
                points.append(parsed)
        values = section.get("values")
        if isinstance(values, list):
            for val in values:
                parsed = _parse_percentage(val)
                if parsed is not None:
                    points.append(parsed)
    return points


def _rank_fashion_terms_from_apify_dataset(data: object) -> list[str]:
    if not isinstance(data, list):
        raise RuntimeError("Apify dataset payload must be a list")

    counter: Counter[str] = Counter()
    for row in data:
        if not isinstance(row, dict):
            continue
        raw_text = row.get("keywordsText")
        if not isinstance(raw_text, str):
            continue
        for term in raw_text.split(","):
            normalized = " ".join(term.strip().lower().split())
            if len(normalized) < 3:
                continue
            if any(hint in normalized for hint in FASHION_HINTS):
                counter[normalized] += 1

    if not counter:
        return FASHION_SEED_KEYWORDS[:3]

    return [kw for kw, _ in counter.most_common(3)]


def _apify_fallback_keywords() -> list[str]:
    dataset_path = Path(os.getenv("APIFY_DATASET_PATH", str(APIFY_DATASET_FALLBACK)))
    if not dataset_path.is_file():
        raise RuntimeError(f"Apify dataset file not found: {dataset_path}")
    try:
        with open(dataset_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    except Exception as exc:
        raise RuntimeError(f"Failed to parse Apify dataset JSON: {exc}") from exc
    return _rank_fashion_terms_from_apify_dataset(data)


def get_live_fashion_trends() -> list[str]:
    """
    Fetch live trends from Serper and return the top 3 seed keywords by rising percentage.

    The function expects SERPER_API_KEY in environment variables or in a local .env file.
    """
    api_key = os.getenv("SERPER_API_KEY") or _load_env_var_from_dotenv("SERPER_API_KEY")
    if not api_key:
        return _apify_fallback_keywords()

    payload = {"keywords": FASHION_SEED_KEYWORDS}
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    try:
        response = httpx.post(SERPER_TRENDS_URL, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError:
        return _apify_fallback_keywords()

    try:
        data = response.json()
    except ValueError:
        return _apify_fallback_keywords()

    keyword_scores: dict[str, float] = {}
    if not isinstance(data, dict):
        return _apify_fallback_keywords()

    trends = data.get("trends")
    if not isinstance(trends, list):
        return _apify_fallback_keywords()

    for trend in trends:
        if not isinstance(trend, dict):
            continue
        keyword = str(trend.get("keyword", "")).strip()
        if keyword not in FASHION_SEED_KEYWORDS:
            continue

        related_queries = trend.get("relatedQueries", {})
        if not isinstance(related_queries, dict):
            continue
        rising_queries = related_queries.get("rising", [])
        if not isinstance(rising_queries, list):
            continue

        interest_over_time = trend.get("interestOverTime", [])
        interest_points = _extract_interest_points(interest_over_time)
        if not interest_points:
            continue

        rising_values: list[float] = []
        for item in rising_queries:
            if not isinstance(item, dict):
                continue
            for candidate_key in ("value", "rising", "percent", "percentage"):
                parsed = _parse_percentage(item.get(candidate_key))
                if parsed is not None:
                    rising_values.append(parsed)
                    break

        if rising_values:
            keyword_scores[keyword] = max(rising_values)

    if not keyword_scores:
        return _apify_fallback_keywords()

    ranked = sorted(keyword_scores.items(), key=lambda kv: kv[1], reverse=True)
    return [keyword for keyword, _ in ranked[:3]]


def _build_description(row: pd.Series) -> str:
    parts: list[str] = []
    name = row.get("prod_name")
    if pd.notna(name) and str(name).strip():
        parts.append(str(name).strip())
    desc = row.get("detail_desc")
    if pd.notna(desc) and str(desc).strip():
        parts.append(str(desc).strip())
    ptype = row.get("product_type_name")
    if pd.notna(ptype) and str(ptype).strip():
        parts.append(str(ptype).strip())
    return " ".join(parts) if parts else "unknown product"


def _parse_keywords_payload(data: object) -> list[str]:
    if isinstance(data, list):
        return [str(x).strip() for x in data if str(x).strip()]
    if isinstance(data, dict):
        for key in ("keywords", "trends", "data", "items"):
            val = data.get(key)
            if isinstance(val, list):
                return [str(x).strip() for x in val if str(x).strip()]
    raise ValueError("Could not parse keywords from JSON (expected list or dict with keywords/trends/data/items)")


class ProductMatch(BaseModel):
    article_id: str
    product_code: str
    prod_name: str
    product_type_name: str | None = None
    detail_desc: str | None = None
    similarity: float = Field(..., description="Cosine similarity to the keyword query embedding [0, 1]")


class RelevantProductsResponse(BaseModel):
    keywords_used: list[str]
    products: list[ProductMatch]


class AppState:
    def __init__(self) -> None:
        self.model: SentenceTransformer | None = None
        self.article_ids: list[str] = []
        self.records: list[dict] = []
        self.embeddings: np.ndarray | None = None
        self.trend_keywords: list[str] = []
        self.trend_merged_norm: np.ndarray | None = None
        self.trend_embeddings: np.ndarray | None = None


state = AppState()


def _load_omni_trends_for_embeddings(model: SentenceTransformer) -> tuple[list[str], np.ndarray | None, np.ndarray | None]:
    path = Path(os.getenv("OMNI_TRENDS_PATH", str(OMNI_TRENDS_FALLBACK)))
    if not path.is_file():
        return [], None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return [], None, None
    items = payload.get("top_keywords") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        return [], None, None
    keywords: list[str] = []
    merged_raw: list[float] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        kw = str(it.get("keyword", "")).strip()
        if not kw:
            continue
        keywords.append(kw)
        try:
            merged_raw.append(float(it.get("merged_score", 0.0)))
        except (TypeError, ValueError):
            merged_raw.append(0.0)
    if not keywords:
        return [], None, None
    merged = np.array(merged_raw, dtype=np.float64)
    if merged.size > 1 and float(merged.max()) > float(merged.min()):
        merged_norm = (merged - merged.min()) / (merged.max() - merged.min())
    else:
        merged_norm = np.ones_like(merged, dtype=np.float64)
    texts = [f"fashion trend: {k}" for k in keywords]
    trend_emb = model.encode(texts, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
    tn = np.linalg.norm(trend_emb, axis=1, keepdims=True)
    tn = np.where(tn == 0, 1.0, tn)
    trend_emb = trend_emb / tn
    return keywords, merged_norm.astype(np.float32), trend_emb


@asynccontextmanager
async def lifespan(app: FastAPI):
    csv_path = Path(os.getenv("ARTICLES_CSV", str(DEFAULT_CSV)))
    if not csv_path.is_file():
        raise RuntimeError(f"articles CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype=str, low_memory=False)
    if "detail_desc" not in df.columns:
        raise RuntimeError("CSV must include a detail_desc column")

    descriptions: list[str] = []
    records: list[dict] = []
    article_ids: list[str] = []

    for _, row in df.iterrows():
        aid = str(row.get("article_id", "")).strip()
        if not aid:
            continue
        text = _build_description(row)
        descriptions.append(text)
        article_ids.append(aid)
        records.append(
            {
                "article_id": aid,
                "product_code": str(row.get("product_code", "") or ""),
                "prod_name": str(row.get("prod_name", "") or ""),
                "product_type_name": None if pd.isna(row.get("product_type_name")) else str(row.get("product_type_name")),
                "detail_desc": None if pd.isna(row.get("detail_desc")) else str(row.get("detail_desc")),
            }
        )

    model = SentenceTransformer(DEFAULT_MODEL)
    emb_chunks: list[np.ndarray] = []
    for i in range(0, len(descriptions), BATCH_SIZE):
        batch = descriptions[i : i + BATCH_SIZE]
        emb_chunks.append(model.encode(batch, convert_to_numpy=True, show_progress_bar=True))
    embeddings = np.vstack(emb_chunks).astype(np.float32)
    # L2-normalize for cosine similarity via dot product
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    embeddings = embeddings / norms

    trend_keywords, trend_merged_norm, trend_embeddings = _load_omni_trends_for_embeddings(model)
    if trend_merged_norm is None or trend_embeddings is None:
        trend_keywords = []
        trend_merged_norm = None
        trend_embeddings = None

    state.model = model
    state.article_ids = article_ids
    state.records = records
    state.embeddings = embeddings
    state.trend_keywords = trend_keywords
    state.trend_merged_norm = trend_merged_norm
    state.trend_embeddings = trend_embeddings

    yield

    state.model = None
    state.embeddings = None
    state.records = []
    state.article_ids = []
    state.trend_keywords = []
    state.trend_merged_norm = None
    state.trend_embeddings = None


app = FastAPI(title="Fashion relevance API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ViabilityRequest(BaseModel):
    concept: str = Field(..., min_length=2, max_length=2000)


class MatchedProduct(BaseModel):
    article_id: str
    product_code: str
    prod_name: str
    product_type_name: str | None = None
    detail_desc: str | None = None
    similarity: float = Field(..., ge=-1.0, le=1.0)
    trend_source: str | None = Field(
        default=None,
        description="Dominant omni channel for the trend best aligned to this SKU (tiktok|instagram|google)",
    )
    shop_url: str | None = Field(
        default=None,
        description="Optional storefront URL from SHOP_PRODUCT_URL_TEMPLATE ({article_id},{product_code},{prod_name})",
    )


class ViabilityResponse(BaseModel):
    verdict: str
    viability_percent: float = Field(..., ge=0, le=100)
    demand_score: float = Field(..., ge=0, le=100)
    saturation_score: float = Field(..., ge=0, le=100)
    similar_product_count: int
    catalog_size: int
    top_trend_match: str | None = None
    top_trend_similarity: float | None = None
    market_reasoning: str
    matched_products: list[MatchedProduct] = Field(default_factory=list)


def _dominant_trend_source(keyword: str | None) -> str | None:
    if not keyword:
        return None
    path = Path(os.getenv("OMNI_TRENDS_PATH", str(OMNI_TRENDS_FALLBACK)))
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    items = payload.get("top_keywords") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None
    key_lower = keyword.strip().lower()
    for it in items:
        if not isinstance(it, dict):
            continue
        if str(it.get("keyword", "")).strip().lower() != key_lower:
            continue
        sources = it.get("sources")
        if not isinstance(sources, dict) or not sources:
            return None
        best = max(sources.items(), key=lambda kv: float(kv[1]) if kv[1] is not None else 0.0)
        return str(best[0])
    return None


def _dominant_trend_keyword_for_product_idx(idx: int) -> str | None:
    if state.trend_embeddings is None or state.trend_merged_norm is None or state.embeddings is None:
        return None
    te = state.trend_embeddings
    tn = state.trend_merged_norm
    if te.shape[0] != tn.shape[0] or idx < 0 or idx >= state.embeddings.shape[0]:
        return None
    p = state.embeddings[idx]
    cos_t = te @ p
    weighted = cos_t * (0.35 + 0.65 * tn)
    best_i = int(np.argmax(weighted))
    if best_i < len(state.trend_keywords):
        return state.trend_keywords[best_i]
    return None


def _product_shop_url(article_id: str, product_code: str, prod_name: str) -> str | None:
    template = os.getenv("SHOP_PRODUCT_URL_TEMPLATE", "").strip()
    if not template:
        return None
    return (
        template.replace("{article_id}", article_id)
        .replace("{product_code}", product_code)
        .replace("{prod_name}", quote(prod_name or "", safe=""))
    )


def _matched_products_for_query(q: np.ndarray, limit: int = 3) -> list[MatchedProduct]:
    if state.embeddings is None:
        return []
    sims = state.embeddings @ q
    order = np.argsort(-sims)
    seen: set[str] = set()
    out: list[MatchedProduct] = []
    for idx in order:
        if len(out) >= limit:
            break
        i = int(idx)
        rec = state.records[i]
        code = str(rec.get("product_code") or rec.get("article_id") or "").strip()
        dedupe_key = code or str(rec.get("article_id"))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        kw = _dominant_trend_keyword_for_product_idx(i)
        src = _dominant_trend_source(kw) if kw else None
        aid = str(rec.get("article_id", ""))
        pcode = str(rec.get("product_code", "") or "")
        pname = str(rec.get("prod_name", "") or "")
        out.append(
            MatchedProduct(
                article_id=aid,
                product_code=pcode,
                prod_name=pname,
                product_type_name=rec.get("product_type_name"),
                detail_desc=rec.get("detail_desc"),
                similarity=round(float(sims[i]), 4),
                trend_source=src,
                shop_url=_product_shop_url(aid, pcode, pname),
            )
        )
    return out


def _viability_verdict(demand: float, saturation: float) -> str:
    high_demand = demand >= 55.0
    low_demand = demand < 38.0
    high_sat = saturation >= 48.0
    if low_demand:
        return "ABORT"
    if high_demand and not high_sat:
        return "GREENLIGHT"
    if high_demand and high_sat:
        return "CAUTION"
    return "CAUTION"


@app.post("/api/viability", response_model=ViabilityResponse)
def production_viability(body: ViabilityRequest) -> ViabilityResponse:
    if state.model is None or state.embeddings is None:
        raise HTTPException(status_code=503, detail="Model not ready")

    concept = body.concept.strip()
    q = state.model.encode([concept], convert_to_numpy=True)[0].astype(np.float32)
    qn = float(np.linalg.norm(q))
    if qn > 0:
        q = q / qn

    trend_emb = state.trend_embeddings
    trend_norm = state.trend_merged_norm
    trend_kws = state.trend_keywords

    if (
        trend_emb is not None
        and trend_emb.shape[0] > 0
        and trend_norm is not None
        and trend_norm.shape[0] == trend_emb.shape[0]
    ):
        cos_t = trend_emb @ q
        weighted = cos_t * (0.35 + 0.65 * trend_norm)
        best_i = int(np.argmax(weighted))
        demand_score = float(np.clip(float(np.max(weighted)) * 100.0, 0.0, 100.0))
        top_trend = trend_kws[best_i] if best_i < len(trend_kws) else None
        top_cos = float(cos_t[best_i])
    else:
        demand_score = 22.0
        top_trend = None
        top_cos = None

    sims = state.embeddings @ q
    n = int(sims.shape[0])
    _sim_raw = os.getenv("VIABILITY_SIM_THRESHOLD", "0.52").strip()
    try:
        sim_threshold = float(_sim_raw) if _sim_raw else 0.52
    except ValueError:
        sim_threshold = 0.52
    similar_count = int(np.sum(sims >= sim_threshold))
    _ref_raw = os.getenv("VIABILITY_SATURATION_REF", "").strip()
    try:
        ref = float(_ref_raw) if _ref_raw else max(80.0, n * 0.004)
    except ValueError:
        ref = max(80.0, n * 0.004)
    saturation_score = float(np.clip(100.0 * similar_count / ref, 0.0, 100.0))

    viability_percent = float(
        np.clip(0.55 * demand_score + 0.45 * (100.0 - saturation_score), 0.0, 100.0)
    )
    verdict = _viability_verdict(demand_score, saturation_score)

    dominant = _dominant_trend_source(top_trend)
    if dominant == "tiktok":
        source_phrase = "High TikTok-side trend strength detected"
    elif dominant == "instagram":
        source_phrase = "Strong Instagram trend signal detected"
    elif dominant:
        source_phrase = f'Elevated "{dominant}" trend contribution detected'
    else:
        source_phrase = ""

    if top_trend and similar_count > 0:
        if source_phrase:
            market_reasoning = (
                f"{source_phrase}, but the warehouse already contains {similar_count} semantically similar listings "
                f"(similarity ≥ {sim_threshold:.2f})—balance demand against overlap."
            )
        else:
            market_reasoning = (
                f'Strong alignment with omni trend "{top_trend}", but the catalog already has '
                f"{similar_count} listings above similarity {sim_threshold:.2f}—watch overlap before you scale."
            )
    elif top_trend:
        if source_phrase:
            market_reasoning = (
                f'{source_phrase} for "{top_trend}", with relatively few close matches in the current assortment.'
            )
        else:
            market_reasoning = (
                f'Demand signal tracks "{top_trend}" from your omni trends, with relatively few close matches '
                "in the current assortment."
            )
    elif similar_count > 0:
        market_reasoning = (
            f"Limited omni-trend signal for this concept; {similar_count} catalog items still look semantically "
            "close—saturation may dominate."
        )
    else:
        market_reasoning = (
            "Weak trend match in omni_trends.json and few close catalog neighbors—treat as unproven until you "
            "refresh trend data or refine the concept."
        )

    matched_products = _matched_products_for_query(q, limit=3)

    return ViabilityResponse(
        verdict=verdict,
        viability_percent=round(viability_percent, 1),
        demand_score=round(demand_score, 1),
        saturation_score=round(saturation_score, 1),
        similar_product_count=similar_count,
        catalog_size=n,
        top_trend_match=top_trend,
        top_trend_similarity=round(top_cos, 4) if top_cos is not None else None,
        market_reasoning=market_reasoning,
        matched_products=matched_products,
    )


async def fetch_trending_keywords(client: httpx.AsyncClient) -> list[str]:
    url = os.getenv("TRENDING_KEYWORDS_URL", "").strip()
    if not url:
        raise HTTPException(
            status_code=503,
            detail="TRENDING_KEYWORDS_URL is not set. Pass ?keywords=... or set the env var.",
        )
    try:
        r = await client.get(url, timeout=30.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Trending API request failed: {e}") from e
    try:
        keywords = _parse_keywords_payload(r.json())
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if not keywords:
        raise HTTPException(status_code=502, detail="Trending API returned no keywords")
    return keywords


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/relevant-products", response_model=RelevantProductsResponse)
async def relevant_products(
    keywords: str | None = Query(
        default=None,
        description="Comma-separated keywords (overrides trending API when provided)",
    ),
) -> RelevantProductsResponse:
    """
    Embeds trending keywords (from Serper trends or TRENDING_KEYWORDS_URL) or the `keywords` query param,
    compares to precomputed product-description embeddings, returns top 10 products by cosine similarity.
    """
    if state.model is None or state.embeddings is None:
        raise HTTPException(status_code=503, detail="Model not ready")

    if keywords is not None and keywords.strip():
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        if not kw_list:
            raise HTTPException(status_code=400, detail="keywords query param is empty")
    else:
        try:
            # Primary source: Serper trends using .env key and seed keywords.
            kw_list = get_live_fashion_trends()
        except RuntimeError as serper_err:
            # Fallback to existing external keyword API if configured.
            async with httpx.AsyncClient() as client:
                try:
                    kw_list = await fetch_trending_keywords(client)
                except HTTPException as fallback_err:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            f"Serper trends failed ({serper_err}). "
                            f"Fallback API also failed ({fallback_err.detail})."
                        ),
                    ) from fallback_err

    query_text = " ".join(kw_list)
    query_emb = state.model.encode([query_text], convert_to_numpy=True)[0].astype(np.float32)
    qn = np.linalg.norm(query_emb)
    if qn > 0:
        query_emb = query_emb / qn

    sims = state.embeddings @ query_emb
    n = int(sims.shape[0])
    take = min(TOP_K, n)
    if take == 0:
        return RelevantProductsResponse(keywords_used=kw_list, products=[])
    kth = take - 1
    top_idx = np.argpartition(-sims, kth)[:take]
    top_idx = top_idx[np.argsort(-sims[top_idx])]

    products: list[ProductMatch] = []
    for i in top_idx:
        rec = state.records[int(i)]
        products.append(
            ProductMatch(
                **rec,
                similarity=float(sims[int(i)]),
            )
        )

    return RelevantProductsResponse(keywords_used=kw_list, products=products)
