/** Corner flower placeholders (SVG) — swap `src` for PNGs later. */
export function FloatingFlowers() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden>
      <FlowerCorner className="flower-float absolute -left-6 bottom-8 w-40 opacity-40 sm:w-52 md:left-4" />
      <FlowerCorner
        className="flower-float absolute -right-4 top-16 w-36 opacity-35 animation-delay-200 sm:w-48 md:right-6"
        mirror
      />
      <FlowerCorner
        className="flower-float animation-delay-400 absolute left-1/4 top-4 w-28 opacity-30 sm:top-8 sm:w-36"
        small
      />
      <FlowerCorner
        className="flower-float animation-delay-150 absolute bottom-20 right-1/4 hidden w-32 opacity-25 md:block"
        mirror
        small
      />
    </div>
  );
}

function FlowerCorner({
  className,
  mirror,
  small,
}: {
  className?: string;
  mirror?: boolean;
  small?: boolean;
}) {
  const scale = small ? 0.85 : 1;
  return (
    <svg
      className={`pointer-events-none ${className ?? ""}`}
      viewBox="0 0 120 120"
      style={{
        transform: mirror ? `scaleX(-1) scale(${scale})` : `scale(${scale})`,
      }}
      fill="none"
    >
      <defs>
        <linearGradient id="petalA" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#E8B4BC" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#F5D0D8" stopOpacity="0.5" />
        </linearGradient>
        <linearGradient id="petalB" x1="100%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#B7C9A8" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#DCE8D2" stopOpacity="0.35" />
        </linearGradient>
      </defs>
      <ellipse cx="60" cy="40" rx="18" ry="32" fill="url(#petalA)" transform="rotate(-25 60 60)" />
      <ellipse cx="60" cy="40" rx="18" ry="32" fill="url(#petalA)" transform="rotate(25 60 60)" />
      <ellipse cx="60" cy="40" rx="18" ry="32" fill="url(#petalA)" transform="rotate(75 60 60)" />
      <ellipse cx="60" cy="40" rx="18" ry="32" fill="url(#petalA)" transform="rotate(115 60 60)" />
      <ellipse cx="60" cy="40" rx="18" ry="32" fill="url(#petalA)" transform="rotate(155 60 60)" />
      <circle cx="60" cy="60" r="14" fill="#DCC48E" fillOpacity="0.45" />
      <ellipse cx="78" cy="88" rx="10" ry="22" fill="url(#petalB)" transform="rotate(12 78 88)" />
      <ellipse cx="42" cy="88" rx="10" ry="22" fill="url(#petalB)" transform="rotate(-12 42 88)" />
    </svg>
  );
}
