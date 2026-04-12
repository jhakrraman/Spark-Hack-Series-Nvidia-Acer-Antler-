import Link from "next/link";

const BOOT_LINES = [
  "[ok] acquiring inference backend .................. nvidia-nim@dgx.local:8000",
  "[ok] loading vlm weights ........................... llama-3.2-11b-vision",
  "[ok] vision ...................................... enabled",
  "[ok] structured output ........................... json_schema enabled",
  "[ok] nyctmc feed catalog ........................ 900+ cameras reachable",
  "[ok] detection schedulers ......................... armed",
  "[ok] local-first — no frames leave this device",
];

export default function Home() {
  return (
    <div className="relative mx-auto max-w-[1600px] px-6 py-12">
      <div className="grid gap-8 lg:grid-cols-[1.2fr_1fr] lg:gap-12">
        {/* Left: wordmark + tagline + CTA */}
        <section className="relative">
          <div className="mb-8 flex items-center gap-3 text-[11px] font-bold uppercase tracking-[0.16em] text-deck-dim">
            <span className="h-px w-10 bg-deck-signal" />
            <span className="text-deck-signal">DECK/01 — ONLINE</span>
          </div>

          <h1 className="font-mono text-[clamp(3.25rem,8.5vw,7.5rem)] font-extrabold leading-[0.92] tracking-tight text-deck-fg">
            PERSON
            <br />
            OF
            <br />
            <span className="text-deck-signal">INTEREST</span>
            <span className="text-deck-signal deck-blink">_</span>
          </h1>

          <div className="mt-10 max-w-[54ch] space-y-4 font-sans text-[15px] font-medium leading-relaxed text-deck-fg/90">
            <p>
              An on-device AI that watches live NYC infrastructure — hundreds of
              public traffic cameras, weather stations, and transit feeds —
              and pipes every frame through a local Gemma 4 vision model.
            </p>
            <p>
              Nothing leaves the box. No rate limits. No API bills. Just a
              tactical HUD for whatever the city is doing right now.
            </p>
          </div>

          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Link href="/pages/nyctmc" className="deck-btn deck-btn--primary">
              ▶ ENTER DECK
            </Link>
            <Link href="/protected" className="deck-btn">
              // DASHBOARD
            </Link>
          </div>

          <div className="mt-16 grid max-w-xl grid-cols-3 gap-6">
            {[
              ["900+", "LIVE CAMS"],
              ["26B", "LOCAL VLM"],
              ["<3s", "FRAME LATENCY"],
            ].map(([val, label]) => (
              <div key={label} className="relative border-l-2 border-deck-line pl-4">
                <div className="deck-num text-3xl font-extrabold text-deck-fg">{val}</div>
                <div className="deck-label mt-2">{label}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Right: boot terminal panel */}
        <section className="relative">
          <div className="deck-panel p-6">
            <div className="mb-4 flex items-center justify-between text-[11px] font-bold uppercase tracking-[0.14em] text-deck-dim">
              <span>/sys/boot</span>
              <span className="flex items-center gap-2 text-deck-ok">
                <span className="deck-dot" />
                ALL SYSTEMS NOMINAL
              </span>
            </div>
            <div className="deck-divider-dash mb-4" />
            <div className="space-y-2 text-[12px] font-medium text-deck-fg">
              {BOOT_LINES.map((line, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="text-deck-faint deck-num tabular-nums w-6 font-bold">{String(i + 1).padStart(2, "0")}</span>
                  <span>
                    {line.startsWith("[ok]") ? (
                      <>
                        <span className="font-bold text-deck-ok">[ok]</span>
                        {line.slice(4)}
                      </>
                    ) : (
                      line
                    )}
                  </span>
                </div>
              ))}
              <div className="pt-3 flex items-center gap-3">
                <span className="text-deck-faint deck-num tabular-nums w-6 font-bold">&gt;_</span>
                <span className="font-bold text-deck-signal">await ./deck start --mode live<span className="deck-blink">_</span></span>
              </div>
            </div>
          </div>

          {/* secondary mini panel */}
          <div className="mt-6 grid grid-cols-2 gap-4">
            <div className="deck-panel p-4">
              <div className="deck-label">NODE</div>
              <div className="mt-2 text-base font-bold text-deck-fg">NYC-001</div>
              <div className="mt-1 text-[11px] font-medium text-deck-dim">Primary Observatory</div>
            </div>
            <div className="deck-panel p-4">
              <div className="deck-label">MODEL</div>
              <div className="mt-2 text-base font-bold text-deck-fg">GEMMA-4-26B</div>
              <div className="mt-1 text-[11px] font-medium text-deck-dim">4B active · MoE · Q4</div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
