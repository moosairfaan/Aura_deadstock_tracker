import { ProductionViabilitySandbox } from "./components/ProductionViabilitySandbox";
import { FloatingFlowers } from "./components/FloatingFlowers";

export default function App() {
  return (
    <div className="relative min-h-screen bg-cream px-4 py-12 sm:px-8">
      <FloatingFlowers />
      <div className="relative z-10 mx-auto max-w-5xl">
        <header className="mb-12 text-center">
          <p className="mb-3 font-sans text-xs font-semibold uppercase tracking-wide text-peony-700/90">
            Fashion engine
          </p>
          <h1 className="aura-logo font-heading text-5xl font-normal tracking-wide text-cocoa sm:text-6xl">
            Aura
          </h1>
          <p className="mt-2 font-heading text-xl font-normal tracking-wide text-cocoa/90 sm:text-2xl">
            Omni Sandbox
          </p>
          <p className="mx-auto mt-5 max-w-2xl font-sans text-sm leading-relaxed text-stone-600 sm:text-base">
            High-end aesthetic intelligence: pastel clarity, glass surfaces, and a single search that fuses omni
            trends with your catalog embeddings.
          </p>
        </header>
        <ProductionViabilitySandbox />
      </div>
    </div>
  );
}
