"use client";

import type { HazardCategory, HazardCategoryId } from "@/types";
import { cn } from "@/lib/utils";

interface CategoryPickerProps {
  categories: HazardCategory[];
  value: HazardCategoryId;
  onChange: (next: HazardCategoryId) => void;
  className?: string;
}

const DEFAULT_CATEGORIES: HazardCategory[] = [
  { id: "all", label: "All hazards", description: "Aggregate risk layer" },
  { id: "violent", label: "Violent", description: "Murder, assault, robbery, weapons" },
  { id: "property", label: "Property", description: "Theft, burglary, larceny" },
  { id: "public_order", label: "Public order", description: "Harassment, trespass, drugs" },
  {
    id: "traffic_hazard",
    label: "Traffic",
    description: "Vision Zero collisions + violations",
  },
  {
    id: "environmental",
    label: "Env",
    description: "311 streetlights, signals, noise",
  },
];

const TIER_COLORS: Record<HazardCategoryId, string> = {
  all: "#67e8f9",
  violent: "#ef4444",
  property: "#f97316",
  public_order: "#a78bfa",
  traffic_hazard: "#eab308",
  environmental: "#22c55e",
};

export function CategoryPicker({
  categories,
  value,
  onChange,
  className,
}: CategoryPickerProps) {
  const list = categories.length > 0 ? categories : DEFAULT_CATEGORIES;

  return (
    <div
      className={cn(
        "pointer-events-auto flex items-center gap-1 rounded-md border border-white/10 bg-black/70 p-1 backdrop-blur-md",
        className
      )}
    >
      <div className="px-2 text-[8px] uppercase tracking-[0.2em] text-white/40">
        LAYER
      </div>
      {list.map((c) => {
        const active = value === c.id;
        const color = TIER_COLORS[c.id] ?? "#67e8f9";
        return (
          <button
            key={c.id}
            type="button"
            onClick={() => onChange(c.id)}
            title={c.description}
            className={cn(
              "rounded-sm border px-2 py-1 text-[9px] font-bold uppercase tracking-[0.14em] transition-all",
              active ? "bg-white/10" : "hover:bg-white/5"
            )}
            style={{
              borderColor: active ? color : `${color}55`,
              color: active ? color : `${color}bb`,
              boxShadow: active ? `0 0 12px ${color}55` : undefined,
            }}
          >
            {c.label}
          </button>
        );
      })}
    </div>
  );
}
