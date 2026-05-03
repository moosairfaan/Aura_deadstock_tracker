export type SeasonId = "summer-26" | "autumn-26" | "winter-26" | "spring-26";

export type SeasonDefinition = {
  id: SeasonId;
  label: string;
  /** Shown on chip, e.g. "Upcoming" */
  status: string;
  /** Fills the main search input */
  searchBarLabel: string;
  /** Sent to /api/viability for richer matching */
  analysisConcept: string;
  keywords: string[];
  aesthetic: string;
  /** Calendar-current season (Summer ’26) → “High Confidence” seasonal fit */
  isCalendarCurrent: boolean;
  tickerQuotes: string[];
};

export const SEASONS: SeasonDefinition[] = [
  {
    id: "summer-26",
    label: "Summer ’26",
    status: "Active",
    searchBarLabel: "Lace & Baby Pink",
    analysisConcept:
      "Lace, Baby Pink, Balloon Pants, 90s Tank Dresses. Fluid fabrics and airy silhouettes. Summer 2026 fashion trends.",
    keywords: ["Lace", "Baby Pink", "Balloon Pants", "90s Tank Dresses"],
    aesthetic: "Fluid fabrics & airy silhouettes.",
    isCalendarCurrent: true,
    tickerQuotes: [
      "Instagram users are obsessed with #PeonyPink this week!",
      "TikTok: #BalloonPants is trending in NYC & London.",
      "Creators are stacking #90sTankDress with sheer layers for sunset content.",
    ],
  },
  {
    id: "autumn-26",
    label: "Autumn ’26",
    status: "Upcoming",
    searchBarLabel: "Chocolate Brown & Brut Denim",
    analysisConcept:
      "Chocolate Brown, Dropped Waists, Brut Denim, Short Trench. Dark romance and tactile textures. Autumn 2026.",
    keywords: ["Chocolate Brown", "Dropped Waists", "Brut Denim", "Short Trench"],
    aesthetic: "Dark Romance & Tactile Textures.",
    isCalendarCurrent: false,
    tickerQuotes: [
      "Pinterest boards are surging for #ChocolateBrown tailoring.",
      "TikTok: #BrutDenim edits are up 40% week-over-week in EU feeds.",
      "Short trenches + dropped waists = the new uniform in Milan street snaps.",
    ],
  },
  {
    id: "winter-26",
    label: "Winter ’26",
    status: "Forecast",
    searchBarLabel: "Winter Brights & Sherpa Vests",
    analysisConcept:
      "Winter Brights Pink, Sheer Hosiery, Sherpa Vests. Minimalist polish and layered textures. Winter 2026.",
    keywords: ["Winter Brights (Pink)", "Sheer Hosiery", "Sherpa Vests"],
    aesthetic: "Minimalist Polish & Layered Textures.",
    isCalendarCurrent: false,
    tickerQuotes: [
      "Instagram: #WinterBrights pink is dominating holiday campaign moodboards.",
      "TikTok velocity on #SherpaVest layering is climbing ahead of cold snaps.",
      "Sheer hosiery + sharp coats = the most-saved pairing this cycle.",
    ],
  },
  {
    id: "spring-26",
    label: "Spring ’26",
    status: "Archive",
    searchBarLabel: "Modern Preppy & Polka Dots",
    analysisConcept:
      "Modern Preppy, Polka Dots, Silk Scarves. Bourgeois chic and soft romance. Spring 2026 archive lens.",
    keywords: ["Modern Preppy", "Polka Dots", "Silk Scarves"],
    aesthetic: "Bourgeois Chic & Soft Romance.",
    isCalendarCurrent: false,
    tickerQuotes: [
      "Archive pull: #PolkaDots resurfacing on editorial IG carousels.",
      "TikTok thriftTok is reviving #SilkScarf necklines for day-to-night.",
      "Modern preppy silhouettes are getting bookmark spikes on LTK.",
    ],
  },
];

export function seasonById(id: SeasonId | null): SeasonDefinition | undefined {
  if (!id) return undefined;
  return SEASONS.find((s) => s.id === id);
}

export function seasonalFitLabel(season: SeasonDefinition | undefined): string {
  if (!season) return "";
  if (season.isCalendarCurrent) return "Seasonal Fit: High Confidence";
  if (season.status === "Upcoming") return "Seasonal Fit: Building Momentum";
  if (season.status === "Archive") return "Seasonal Fit: Archive Lens";
  return "Seasonal Fit: Directional Signal";
}
