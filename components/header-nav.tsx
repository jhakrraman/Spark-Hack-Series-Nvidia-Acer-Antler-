"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/pages/nyctmc", label: "NYC DECK", code: "01" },
  { href: "/pages/map", label: "MAP", code: "02" },
  { href: "/pages/realtimeStreamPage", label: "REALTIME", code: "03" },
  { href: "/pages/upload", label: "UPLOAD", code: "04" },
  { href: "/pages/saved-videos", label: "LIBRARY", code: "05" },
  { href: "/pages/statistics", label: "STATS", code: "06" },
];

export function HeaderNav() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1">
      {ITEMS.map((item) => {
        const active = pathname?.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`group flex items-center gap-2 px-3 py-2 text-[11px] font-bold uppercase tracking-[0.14em] transition-colors ${
              active
                ? "text-deck-signal"
                : "text-deck-dim hover:text-deck-fg"
            }`}
          >
            <span className="deck-num text-[10px] font-bold text-deck-faint group-hover:text-deck-dim">
              {item.code}
            </span>
            <span>{item.label}</span>
            {active && <span className="deck-dot h-1.5 w-1.5 text-deck-signal" />}
          </Link>
        );
      })}
    </nav>
  );
}
