const iconWrap =
  "inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/30 bg-white/40 text-xs backdrop-blur-sm";

export function TrendSourceIcons({
  variant,
  trendSource,
  sessionFlags,
}: {
  variant: "session" | "sku";
  trendSource?: string | null;
  sessionFlags?: Record<string, boolean>;
}) {
  const active = (key: string) => {
    const k = key.toLowerCase();
    if (variant === "sku") return (trendSource || "").toLowerCase() === k;
    return Boolean(sessionFlags?.[k]);
  };

  return (
    <div className="flex items-center gap-1.5" title="Trend signal origin">
      <span
        className={`${iconWrap} ${
          active("tiktok") ? "text-peony ring-1 ring-peony/40" : "text-stone-400 opacity-60"
        }`}
      >
        <MusicIcon />
      </span>
      <span
        className={`${iconWrap} ${
          active("instagram") ? "text-sage ring-1 ring-sage/50" : "text-stone-400 opacity-60"
        }`}
      >
        <CameraIcon />
      </span>
      <span
        className={`${iconWrap} ${
          active("google") ? "text-palegold ring-1 ring-palegold/50" : "text-stone-400 opacity-60"
        }`}
      >
        <SearchIcon />
      </span>
    </div>
  );
}

function MusicIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
    </svg>
  );
}

function CameraIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" />
    </svg>
  );
}
