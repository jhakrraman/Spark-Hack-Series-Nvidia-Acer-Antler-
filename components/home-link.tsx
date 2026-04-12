import Link from "next/link";

// DECK/01 wordmark. Primary home link for the app shell.
export default function HomeLink() {
  return (
    <Link
      href="/"
      className="group flex items-center gap-3 text-deck-fg hover:text-deck-signal transition-colors"
    >
      <span className="deck-num text-[11px] font-bold uppercase tracking-[0.18em] text-deck-faint group-hover:text-deck-dim">
        DECK/01
      </span>
      <span className="h-5 w-px bg-deck-line" />
      <span className="text-[15px] font-extrabold uppercase tracking-[0.18em]">
        PERSON<span className="text-deck-signal">.</span>OF<span className="text-deck-signal">.</span>INTEREST
      </span>
    </Link>
  );
}
