import { FormEvent, useState } from "react";
import { seasonById, seasonalFitLabel, type SeasonDefinition, type SeasonId } from "../data/seasonalCategories";
import { SeasonalDiscoveryBar } from "./SeasonalDiscoveryBar";
import { TrendSourceIcons } from "./TrendSourceIcons";

type MatchedProduct = {
  article_id: string;
  product_code: string;
  prod_name: string;
  product_type_name: string | null;
  detail_desc: string | null;
  similarity: number;
  trend_source: string | null;
  shop_url?: string | null;
};

/** Opens in a new tab: API `shop_url`, then Vite template, then Google Shopping search. */
function resolveShopUrl(p: MatchedProduct): string {
  const fromApi = p.shop_url?.trim();
  if (fromApi && /^https?:\/\//i.test(fromApi)) return fromApi;

  const tmpl = (import.meta.env.VITE_SHOP_PRODUCT_URL_TEMPLATE as string | undefined)?.trim();
  if (tmpl) {
    return tmpl
      .replaceAll("{article_id}", encodeURIComponent(p.article_id))
      .replaceAll("{product_code}", encodeURIComponent(p.product_code))
      .replaceAll("{prod_name}", encodeURIComponent(p.prod_name || ""));
  }

  const q = [p.prod_name, p.product_code, p.article_id].filter(Boolean).join(" ");
  return `https://www.google.com/search?tbm=shop&q=${encodeURIComponent(q)}`;
}

type ViabilityResponse = {
  verdict: string;
  viability_percent: number;
  demand_score: number;
  saturation_score: number;
  similar_product_count: number;
  catalog_size: number;
  top_trend_match: string | null;
  top_trend_similarity: number | null;
  market_reasoning: string;
  matched_products: MatchedProduct[];
};

function verdictStyle(verdict: string): { label: string; ring: string; badge: string } {
  const v = verdict.toUpperCase();
  if (v === "GREENLIGHT") {
    return {
      label: "GREENLIGHT",
      ring: "ring-sage/50",
      badge: "bg-sage/25 text-emerald-900 ring-1 ring-sage/40",
    };
  }
  if (v === "CAUTION") {
    return {
      label: "CAUTION",
      ring: "ring-palegold/60",
      badge: "bg-palegold/30 text-amber-900 ring-1 ring-palegold/50",
    };
  }
  return {
    label: "ABORT",
    ring: "ring-peony/50",
    badge: "bg-peony/25 text-rose-900 ring-1 ring-peony/45",
  };
}

export function ProductionViabilitySandbox() {
  const [concept, setConcept] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ViabilityResponse | null>(null);
  const [selectedSeasonId, setSelectedSeasonId] = useState<SeasonId>("summer-26");
  /** When set, last successful run came from a seasonal card (drives fit copy + forecast UI). */
  const [seasonRunId, setSeasonRunId] = useState<SeasonId | null>(null);

  async function runAnalysis(query: string, fromSeason: SeasonId | null) {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setError("Enter a product concept (at least 2 characters).");
      return;
    }
    setError(null);
    setResult(null);
    setLoading(true);
    setSeasonRunId(fromSeason);
    try {
      const res = await fetch("/api/viability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ concept: trimmed }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed (${res.status})`);
      }
      const data: ViabilityResponse = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed.");
      setSeasonRunId(null);
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await runAnalysis(concept, null);
  }

  function handleSeasonSelect(season: SeasonDefinition) {
    setSelectedSeasonId(season.id);
    setConcept(season.searchBarLabel);
    void runAnalysis(season.analysisConcept, season.id);
  }

  const styles = result ? verdictStyle(result.verdict) : null;

  return (
    <div className="relative z-10 space-y-10">
      <form onSubmit={onSubmit} className="relative z-20 isolate">
        <div className="rounded-2xl border border-white/20 bg-white/35 p-1 shadow-glass backdrop-blur-md">
          <div className="flex flex-col gap-3 rounded-xl bg-white/25 p-3 sm:flex-row sm:items-center sm:gap-4 sm:p-4">
            <div className="flex-1">
              <label htmlFor="concept" className="sr-only">
                Search your fashion concept
              </label>
              <input
                id="concept"
                type="text"
                value={concept}
                onChange={(e) => setConcept(e.target.value)}
                placeholder="Try: Slim fit tshirt, linen blazer, quiet luxury knit…"
                className="w-full rounded-xl border border-white/20 bg-white/50 px-4 py-3.5 font-sans text-base text-stone-800 placeholder:text-stone-400 focus:border-peony/50 focus:outline-none focus:ring-2 focus:ring-peony/25"
                autoComplete="off"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="shrink-0 rounded-full border border-white/50 bg-gradient-to-r from-pink-200 to-pastelyellow px-8 py-3.5 font-sans text-sm font-semibold tracking-wide text-cocoa shadow-md shadow-peony/15 transition hover:brightness-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-peony/35 focus-visible:ring-offset-2 focus-visible:ring-offset-cream disabled:cursor-not-allowed disabled:opacity-55"
            >
              {loading ? "Analyzing…" : "Analyze"}
            </button>
          </div>
        </div>
      </form>

      <SeasonalDiscoveryBar activeId={selectedSeasonId} onSelect={handleSeasonSelect} />

      {error && (
        <div className="rounded-2xl border border-peony/40 bg-peony/15 px-4 py-3 text-sm text-rose-900 backdrop-blur-md">
          {error}
        </div>
      )}

      {result && styles && (
        <>
          <section
            className={`relative overflow-hidden rounded-2xl border border-white/20 bg-white/40 p-6 shadow-glass backdrop-blur-md ring-1 sm:p-8 ${styles.ring}`}
          >
            <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-peony/20 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-20 -left-10 h-48 w-48 rounded-full bg-sage/25 blur-3xl" />

            <div className="relative flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-xl">
                <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                  Decision matrix
                </p>
                <h2 className="mt-2 font-heading text-3xl font-normal tracking-wide text-cocoa sm:text-4xl">
                  Viability
                </h2>
                <p className="mt-2 font-sans text-sm leading-relaxed text-stone-600">
                  Demand from omni trend vectors · Saturation from catalog overlap on{" "}
                  <span className="font-medium text-stone-800">{result.catalog_size.toLocaleString()}</span> SKUs
                </p>
                {(() => {
                  const seasonCtx = seasonRunId ? seasonById(seasonRunId) : undefined;
                  if (!seasonCtx) return null;
                  return (
                    <div className="mt-5 flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full px-3 py-1.5 font-sans text-xs font-semibold tracking-wide ${
                          seasonCtx.isCalendarCurrent
                            ? "bg-peony/30 text-peony-900 ring-1 ring-peony/40"
                            : "bg-matchamint/40 text-sage-900 ring-1 ring-matchamint/55"
                        }`}
                      >
                        {seasonalFitLabel(seasonCtx)}
                      </span>
                      <span className="group relative inline-flex items-center">
                        <button
                          type="button"
                          className="flex h-7 w-7 cursor-help items-center justify-center rounded-full border border-white/35 bg-white/55 text-[10px] font-bold text-stone-600 shadow-sm backdrop-blur-sm"
                          aria-describedby="trend-forecast-tip"
                        >
                          i
                        </button>
                        <span
                          id="trend-forecast-tip"
                          role="tooltip"
                          className="pointer-events-none invisible absolute bottom-full left-0 z-30 mb-2 w-[min(16rem,calc(100vw-2rem))] rounded-xl border border-white/35 bg-white/95 px-3 py-2 text-left text-[11px] leading-snug text-stone-700 opacity-0 shadow-lg backdrop-blur-md transition duration-150 group-hover:visible group-hover:opacity-100 sm:left-auto sm:right-0"
                        >
                          Predicted to peak in 3 weeks based on TikTok velocity.
                        </span>
                      </span>
                    </div>
                  );
                })()}
              </div>
              <div
                className={`inline-flex items-center self-start rounded-full px-5 py-2 font-sans text-sm font-bold tracking-wide ${styles.badge}`}
              >
                {styles.label}
              </div>
            </div>

            <div className="relative mt-8 grid gap-4 sm:grid-cols-3">
              <Metric label="Demand score" value={result.demand_score} suffix="/ 100" hint="Trend alignment" />
              <Metric label="Saturation" value={result.saturation_score} suffix="/ 100" hint="Catalog overlap" />
              <Metric
                label="Similar SKUs"
                value={result.similar_product_count}
                suffix={` / ${result.catalog_size.toLocaleString()}`}
                hint="Above similarity threshold"
              />
            </div>

            <div className="relative mt-10 grid gap-10 lg:grid-cols-2 lg:items-center">
              <div>
                <div className="mb-3 flex items-center justify-between font-sans text-xs uppercase tracking-wide text-stone-500">
                  <span>Viability gauge</span>
                  <span className="text-lg font-semibold tabular-nums tracking-wide text-cocoa">
                    {result.viability_percent}%
                  </span>
                </div>
                <ViabilityGauge value={result.viability_percent} />
                <p className="mt-2 text-center text-[11px] text-stone-500">Peach → mint spectrum</p>
              </div>

              <div className="rounded-2xl border border-white/20 bg-white/35 p-5 backdrop-blur-md">
                <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Omni read</p>
                {result.top_trend_match ? (
                  <p className="mt-2 text-sm text-stone-700">
                    Top keyword match:{" "}
                    <span className="font-medium text-stone-900">{result.top_trend_match}</span>
                    {result.top_trend_similarity != null && (
                      <span className="text-stone-500"> · cos {result.top_trend_similarity}</span>
                    )}
                  </p>
                ) : (
                  <p className="mt-2 text-sm text-stone-600">No strong omni keyword lock for this phrasing yet.</p>
                )}
                <p className="mt-4 border-t border-white/20 pt-4 text-sm leading-relaxed text-stone-700">
                  {result.market_reasoning}
                </p>
              </div>
            </div>
          </section>

          <section>
            <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Omni-feed</p>
                <h3 className="font-heading text-2xl font-normal tracking-wide text-cocoa">Matched inventory</h3>
                <p className="font-sans text-sm text-stone-600">Closest catalog neighbors to your search concept.</p>
              </div>
            </div>
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {result.matched_products.map((p) => (
                <article
                  key={p.article_id}
                  className="group relative overflow-hidden rounded-2xl border border-white/20 bg-white/45 shadow-glass backdrop-blur-md transition duration-300 ease-out hover:z-[1] hover:scale-[1.02] hover:shadow-xl"
                >
                  <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-peony/10 via-transparent to-sage/15 opacity-0 transition group-hover:opacity-100" />
                  <div className="relative flex flex-col p-5">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-sans text-lg font-semibold leading-snug tracking-wide text-cocoa">
                        {p.prod_name || "Untitled"}
                      </h4>
                      <TrendSourceIcons variant="sku" trendSource={p.trend_source} />
                    </div>
                    {p.product_type_name && (
                      <p className="mt-1 text-xs uppercase tracking-wider text-stone-500">{p.product_type_name}</p>
                    )}
                    <p className="mt-3 line-clamp-3 text-sm text-stone-600">{p.detail_desc || "—"}</p>
                    <div className="mt-4 flex items-center justify-between gap-2">
                      <span className="font-mono text-xs text-stone-500">sim {p.similarity.toFixed(3)}</span>
                      <a
                        href={resolveShopUrl(p)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="rounded-full border border-white/50 bg-gradient-to-r from-pink-200 to-pastelyellow px-5 py-2 font-sans text-xs font-semibold tracking-wide text-cocoa opacity-0 shadow-md shadow-peony/15 backdrop-blur-sm transition duration-300 hover:brightness-105 pointer-events-none group-hover:pointer-events-auto group-hover:opacity-100"
                      >
                        Shop the trend
                      </a>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function ViabilityGauge({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  const pathLength = 100;
  return (
    <svg viewBox="0 0 200 108" className="mx-auto w-full max-w-[280px]" aria-label={`Viability ${pct}%`}>
      <defs>
        <linearGradient id="gaugePeachMint" x1="0%" y1="50%" x2="100%" y2="50%">
          <stop offset="0%" stopColor="#FDBA9A" />
          <stop offset="55%" stopColor="#F5D0A8" />
          <stop offset="100%" stopColor="#86EFAC" />
        </linearGradient>
      </defs>
      <path
        d="M 24 96 A 76 76 0 0 1 176 96"
        pathLength={pathLength}
        fill="none"
        stroke="rgba(255,255,255,0.65)"
        strokeWidth="14"
        strokeLinecap="round"
      />
      <path
        d="M 24 96 A 76 76 0 0 1 176 96"
        pathLength={pathLength}
        fill="none"
        stroke="url(#gaugePeachMint)"
        strokeWidth="14"
        strokeLinecap="round"
        strokeDasharray={`${(pct / 100) * pathLength} ${pathLength}`}
        className="transition-[stroke-dasharray] duration-700 ease-out"
      />
    </svg>
  );
}

function Metric({
  label,
  value,
  suffix,
  hint,
}: {
  label: string;
  value: number;
  suffix: string;
  hint: string;
}) {
  return (
    <div className="rounded-xl border border-white/20 bg-white/40 px-4 py-3 backdrop-blur-sm">
      <p className="text-xs uppercase tracking-wider text-stone-500">{label}</p>
      <p className="mt-1 font-sans text-xl font-semibold tabular-nums tracking-wide text-cocoa">
        {typeof value === "number" && !Number.isInteger(value) ? value.toFixed(1) : value}
        <span className="text-sm font-normal text-stone-500">{suffix}</span>
      </p>
      <p className="mt-0.5 text-[11px] text-stone-500">{hint}</p>
    </div>
  );
}
