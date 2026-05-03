import type { SeasonDefinition, SeasonId } from "../data/seasonalCategories";
import { SEASONS } from "../data/seasonalCategories";

type Props = {
  activeId: SeasonId;
  onSelect: (season: SeasonDefinition) => void;
};

/** Optional PNGs: place files at `/public/seasonal/summer.png` etc. and set `image` on each season in data if desired. */
export function SeasonalDiscoveryBar({ activeId, onSelect }: Props) {
  const activeSeason = SEASONS.find((s) => s.id === activeId) ?? SEASONS[0];

  return (
    <div className="relative mt-8">
      <BarFlower className="pointer-events-none absolute -left-1 top-1/2 z-[1] hidden h-14 w-14 -translate-y-1/2 opacity-50 sm:block" />
      <BarFlower
        className="pointer-events-none absolute -right-1 top-1/2 z-[1] hidden h-14 w-14 -translate-y-1/2 scale-x-[-1] opacity-50 sm:block"
        delay
      />

      <div className="relative rounded-2xl border border-white/25 bg-white/30 px-3 py-4 shadow-glass backdrop-blur-md sm:px-5">
        <p className="mb-3 text-center font-heading text-xs font-normal uppercase tracking-wide text-cocoa">
          Seasonal discovery
        </p>

        <div className="hide-scrollbar flex gap-3 overflow-x-auto pb-1 pt-0.5 [-webkit-overflow-scrolling:touch]">
          {SEASONS.map((season) => {
            const isActive = season.id === activeId;
            return (
              <button
                key={season.id}
                type="button"
                onClick={() => onSelect(season)}
                className={`group flex min-w-[11.5rem] shrink-0 flex-col rounded-2xl border px-4 py-3 text-left shadow-sm backdrop-blur-md transition-all duration-300 hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-peony/40 sm:min-w-[13rem] ${
                  isActive
                    ? "border-peony/50 bg-peony/20 ring-1 ring-peony/30"
                    : "border-matchamint/45 bg-matchamint/15 ring-0 hover:border-matchamint/60 hover:bg-matchamint/25"
                }`}
              >
                <span className="mb-1 flex items-center gap-2">
                  <SeasonGlyph id={season.id} />
                  <span
                    className={`font-sans text-sm font-semibold tracking-wide ${
                      isActive ? "text-peony-900" : "text-sage-900"
                    }`}
                  >
                    {season.label}
                  </span>
                </span>
                <span className="text-[10px] font-medium uppercase tracking-wider text-stone-500">{season.status}</span>
                <p className="mt-2 line-clamp-2 text-[11px] leading-snug text-stone-600">{season.aesthetic}</p>
              </button>
            );
          })}
        </div>

        <div className="relative mt-4 overflow-hidden rounded-xl border border-white/20 bg-white/40 py-2">
          <div className="ticker-track flex gap-10 whitespace-nowrap px-4">
            {[...activeSeason.tickerQuotes, ...activeSeason.tickerQuotes].map((line, i) => (
              <span key={i} className="inline-flex shrink-0 items-center gap-2 font-sans text-xs text-stone-700">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-peony" aria-hidden />
                {line}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SeasonGlyph({ id }: { id: SeasonId }) {
  const cls = "h-8 w-8 shrink-0 drop-shadow-sm";
  switch (id) {
    case "summer-26":
      return (
        <svg className={cls} viewBox="0 0 32 32" aria-hidden>
          <circle cx="16" cy="16" r="7" fill="#FCD34D" stroke="#F59E0B" strokeWidth="1.2" />
            {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => {
              const rad = (deg * Math.PI) / 180;
              return (
                <line
                  key={deg}
                  x1="16"
                  y1="16"
                  x2={16 + 11 * Math.cos(rad)}
                  y2={16 + 11 * Math.sin(rad)}
                  stroke="#FBBF24"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              );
            })}
        </svg>
      );
    case "autumn-26":
      return (
        <svg className={cls} viewBox="0 0 32 32" aria-hidden>
          <path
            d="M16 4 C10 12 6 18 8 24c2 5 8 6 8 6s6-1 8-6c2-6-2-12-8-20z"
            fill="#C2410C"
            opacity="0.9"
          />
          <path d="M16 22v8" stroke="#92400E" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "winter-26":
      return (
        <svg className={cls} viewBox="0 0 32 32" aria-hidden>
          <g stroke="#7DD3FC" strokeWidth="1.2" fill="none">
            <path d="M16 4v24M4 16h24M7 7l18 18M25 7L7 25" />
            <circle cx="16" cy="16" r="3" fill="#E0F2FE" stroke="#38BDF8" />
          </g>
        </svg>
      );
    default:
      return (
        <svg className={cls} viewBox="0 0 32 32" aria-hidden>
          <path
            d="M8 24c4-8 8-12 16-14 2 6 0 12-4 16-4-2-8-2-12-2z"
            fill="#86EFAC"
            stroke="#4ADE80"
            strokeWidth="1"
          />
          <ellipse cx="22" cy="10" rx="3" ry="5" fill="#BBF7D0" transform="rotate(-20 22 10)" />
        </svg>
      );
  }
}

function BarFlower({ className, delay }: { className?: string; delay?: boolean }) {
  return (
    <svg className={`flower-float ${delay ? "animation-delay-200" : ""} ${className ?? ""}`} viewBox="0 0 64 64" fill="none" aria-hidden>
      <ellipse cx="32" cy="22" rx="10" ry="18" fill="#E8B4BC" fillOpacity="0.85" transform="rotate(-20 32 32)" />
      <ellipse cx="32" cy="22" rx="10" ry="18" fill="#E8B4BC" fillOpacity="0.85" transform="rotate(20 32 32)" />
      <ellipse cx="32" cy="22" rx="10" ry="18" fill="#B7C9A8" fillOpacity="0.7" transform="rotate(90 32 32)" />
      <circle cx="32" cy="34" r="8" fill="#DCC48E" fillOpacity="0.55" />
    </svg>
  );
}
